#!/usr/bin/env python3
"""
FastMCP ExtraETF Server

Exposes ETF holdings, factsheets, allocations, and dividend data
from extraetf.com through MCP tools for AI agents.

How it works:
  The server fetches the ETF profile page (extraetf.com/de/etf-profile/{ISIN})
  and extracts structured data from the embedded
  `<script id="frontend-state" type="application/json">` tag on the page.
  ExtraETF embeds a complete JSON snapshot of the ETF's holdings,
  allocation, dividend history, and key facts directly in the HTML —
  no API key or web scraping of individual elements is needed.
  The JSON is parsed and returned as MCP tool responses. A simple
  in-memory cache (5-minute TTL) avoids re-fetching the same page
  within a session. Only ISINs eligible for the ExtraETF coverage
  (primarily UCITS ETFs listed in Europe) are supported; individual
  US stocks will return a 404.
"""

import json
import ssl
import time
import urllib.request

from fastmcp import FastMCP

mcp = FastMCP("ExtraETF")

_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300  # 5 minutes

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
}

_SSL_CONTEXT = ssl.create_default_context()


def _fetch_page(isin: str) -> str:
    url = f"https://extraetf.com/de/etf-profile/{isin}"
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"extraetf.com returned HTTP {e.code} for ISIN {isin}. "
            "Verify the ISIN is correct and the ETF is listed on extraetf.com."
        )
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching ISIN {isin}: {e.reason}")


def _extract_json(html: str) -> dict:
    marker = '<script id="frontend-state" type="application/json">'
    start = html.find(marker)
    if start < 0:
        raise RuntimeError(
            "Could not find ETF data in page. "
            "Verify the ISIN is correct and the ETF is listed on extraetf.com."
        )
    start += len(marker)
    end = html.find("</script>", start)
    content = html[start:end].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed JSON from extraetf.com: {e}")


def _get_etf_data(isin: str) -> dict:
    now = time.time()
    if isin in _CACHE and (now - _CACHE[isin][0]) < _CACHE_TTL:
        return _CACHE[isin][1]

    html = _fetch_page(isin)
    data = _extract_json(html)

    for k, v in data.items():
        if isinstance(v, dict) and "b" in v and "results" in v["b"]:
            results = v["b"]["results"]
            if not results:
                continue
            result = results[0]
            _CACHE[isin] = (now, result)
            return result

    raise RuntimeError(f"No ETF data found for ISIN {isin}")


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool
def ping() -> dict:
    """Health check — verify the MCP server is running and responsive.

    Returns:
        status: "ok"
        message: server description
    """
    return {"status": "ok", "message": "ExtraETF MCP running"}


@mcp.tool
def get_etf_holdings(isin: str) -> dict:
    """Get the top holdings for an ETF by ISIN.

    Each holding includes name, ISIN, weight as a percentage of the portfolio,
    sector, country, and currency. The number of top holdings varies per ETF
    (typically 10–15).

    Args:
        isin: 12-character ISIN code (e.g. "IE00B1YZSC51" for iShares Core
              MSCI Europe UCITS ETF)

    Returns:
        isin: the ISIN queried
        name: full ETF name
        total_holdings: total number of positions
        stock_holdings: number of equity positions
        top_holdings_weight_pct: combined weight of the returned top holdings
        holdings: list of {name, isin, weight_pct, sector, country, currency}
    """
    data = _get_etf_data(isin)
    items = data.get("portfolio_breakdown", {}).get("items", [])
    return {
        "isin": data.get("isin"),
        "name": data.get("fondname"),
        "total_holdings": data.get("number_of_holding"),
        "stock_holdings": data.get("number_of_stockholding"),
        "top_holdings_weight_pct": round(data.get("portfolio_items_weight", 0), 2),
        "holdings": [
            {
                "name": item.get("name"),
                "isin": item.get("isin"),
                "weight_pct": round(item.get("weight", 0), 2),
                "sector": item.get("stock_global_sector"),
                "country": item.get("country_name"),
                "currency": item.get("local_currency_code"),
            }
            for item in items
        ],
    }


@mcp.tool
def get_etf_allocation(isin: str) -> dict:
    """Get the allocation breakdown of an ETF by ISIN.

    Returns country, region, sector, currency, and asset class allocations
    as percentage weights. Useful for understanding geographic and sector
    diversification.

    Args:
        isin: 12-character ISIN code

    Returns:
        isin: the ISIN queried
        name: full ETF name
        asset_allocation: breakdown by asset class (stock, bond, cash, etc.)
        country_allocation: list of {country, weight_pct}
        region_allocation: list of {region, weight_pct}
        sector_allocation: list of {sector, weight_pct}
        currency_allocation: list of {currency, weight_pct}
    """
    data = _get_etf_data(isin)
    pb = data.get("portfolio_breakdown", {})

    def _to_list(exposure, key="name"):
        if not exposure:
            return []
        if isinstance(exposure, dict):
            return [{"name": k, "weight_pct": round(v, 2)} for k, v in exposure.items()]
        if isinstance(exposure, list):
            return [
                {
                    "name": item.get(key),
                    "weight_pct": round(item.get("value", 0), 2),
                }
                for item in exposure
            ]
        return []

    return {
        "isin": data.get("isin"),
        "name": data.get("fondname"),
        "asset_allocation": _to_list(pb.get("asset_allocation_exposure_list")),
        "country_allocation": _to_list(pb.get("country_stocks_exposure_list")),
        "region_allocation": _to_list(pb.get("region_stock_exposure_list")),
        "sector_allocation": _to_list(pb.get("global_stock_exposure_list")),
        "currency_allocation": _to_list(pb.get("currency_allocations")),
    }


@mcp.tool
def get_etf_factsheet(isin: str) -> dict:
    """Get a comprehensive factsheet for an ETF by ISIN.

    Returns key statistics including costs (TER), fund size, replication
    method, performance figures, risk metrics, and basic fund information.

    Args:
        isin: 12-character ISIN code

    Returns:
        isin: the ISIN queried
        name: full ETF name
        wkn: German securities identifier
        ticker: trading symbol
        ter_pct: total expense ratio
        fund_size_m: net assets in millions
        fund_currency: fund currency
        fund_domicile: country of domicile
        launch_date: inception date
        replication_method: physical or synthetic
        replication_type: full or optimized
        distribution_policy: accumulating or distributing
        distribution_interval: frequency of distributions
        index_name: underlying index
        total_holdings: number of positions
        securities_lending: whether the fund engages in securities lending
        ongoing_charges_pct: ongoing charges figure date
        performance: {1y, 3y, 5y, ytd, since_launch} returns in EUR
        risk: {volatility_1y, volatility_3y, max_drawdown_1y, max_drawdown_3y,
               sharpe_ratio_1y, sharpe_ratio_3y}
        tracking_difference_1y: annual tracking difference over 1 year
        tracking_difference_3y: annual tracking difference over 3 years
    """
    data = _get_etf_data(isin)

    returns = {
        k: v
        for k, v in {
            "1y": data.get("return_1_year_real"),
            "3y": data.get("return_3_years_ago_real"),
            "5y": data.get("return_5_years_ago_real"),
            "ytd": data.get("return_year_to_date_real"),
            "since_launch": data.get("return_since_launch_real"),
        }.items()
        if v is not None
    }

    risk = {}
    for src, dst in [
        ("sd_1y", "volatility_1y"),
        ("sd_3y", "volatility_3y"),
        ("sd_5y", "volatility_5y"),
        ("max_drawdown_1y_name", "max_drawdown_1y"),
        ("max_drawdown_3y_name", "max_drawdown_3y"),
        ("sharpe_ratio_1_year", "sharpe_ratio_1y"),
        ("sharpe_ratio_3_years", "sharpe_ratio_3y"),
    ]:
        val = data.get(src) if data.get(src) is not None else data.get(dst)
        if val is not None:
            risk[dst] = round(val, 2) if isinstance(val, float) else val

    return {
        "isin": data.get("isin"),
        "name": data.get("fondname"),
        "short_name": data.get("shortname"),
        "wkn": data.get("wkn"),
        "ticker": data.get("trading_symbol_xetra"),
        "ter_pct": data.get("ter"),
        "ongoing_charges_pct": data.get("ongoing_charges"),
        "fund_size_m": data.get("net_assets"),
        "fund_size_date": data.get("net_assets_date"),
        "fund_currency": data.get("fund_currency_id"),
        "fund_domicile": data.get("fund_domicile"),
        "launch_date": data.get("launch_date"),
        "replication_method": data.get("replication_methodology_first_level"),
        "replication_type": data.get("replication_methodology_second_level"),
        "distribution_policy": data.get("distribution_policy"),
        "distribution_interval": data.get("distribution_interval"),
        "index_name": data.get("index_name"),
        "total_holdings": data.get("number_of_holding"),
        "stock_holdings": data.get("number_of_stockholding"),
        "securities_lending": data.get("has_securities_lending"),
        "performance_pct": returns,
        "risk": risk,
        "tracking_difference_1y": data.get("tracking_difference_mean_yearly_sort"),
        "current_nav": data.get("nav"),
        "nav_date": data.get("nav_date"),
        "description": data.get("description"),
    }


@mcp.tool
def get_etf_dividends(isin: str) -> dict:
    """Get the dividend history for an ETF by ISIN.

    Returns annual per-unit distributions, historical yield percentages,
    and detailed per-payment records with ex-date, pay-date, and amounts
    in multiple currencies (EUR, USD, CHF, GBP, etc.).

    Args:
        isin: 12-character ISIN code

    Returns:
        isin: the ISIN queried
        name: full ETF name
        distribution_policy: accumulating or distributing
        distribution_interval: frequency of payments
        yield_history: dict mapping year strings to yield percentages
        annual_distributions: dict mapping year strings to EUR/unit amounts
        detail: list of {ex_date, pay_date, total_eur, year}
        dividend_cagr: compound annual growth rates for various periods
    """
    data = _get_etf_data(isin)
    dist_months = data.get("distribution_frequency_months", {})
    yields = data.get("yield_distribution", {})
    sum_dist = data.get("sum_distribution", {})
    cagr = data.get("distribution_cagr", {})

    detail = []
    for year_key, payments in dist_months.items():
        if not isinstance(payments, list):
            continue
        for p in payments:
            detail.append(
                {
                    "ex_date": p.get("ex_date", ""),
                    "pay_date": p.get("pay_date", ""),
                    "total_eur": p.get("total"),
                    "total_usd": p.get("total_in_usd"),
                    "total_chf": p.get("total_in_chf"),
                    "total_gbp": p.get("total_in_gbp"),
                    "year": year_key,
                }
            )

    detail.sort(key=lambda x: x.get("ex_date", ""))

    return {
        "isin": data.get("isin"),
        "name": data.get("fondname"),
        "distribution_policy": data.get("distribution_policy"),
        "distribution_interval": data.get("distribution_interval"),
        "yield_history": {
            k: round(v, 2) if isinstance(v, (int, float)) else v
            for k, v in yields.items()
            if v is not None
        },
        "annual_distributions_eur": {
            k: round(v, 2) if isinstance(v, (int, float)) else v
            for k, v in sum_dist.items()
            if v is not None
        },
        "detail": detail,
        "dividend_cagr_pct": {
            k: round(v * 100, 2) if isinstance(v, (int, float)) else v
            for k, v in cagr.items()
            if v is not None
        },
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("ExtraETF MCP running")
    mcp.run()
