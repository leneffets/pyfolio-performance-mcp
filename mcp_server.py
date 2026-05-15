#!/usr/bin/env python3
"""
FastMCP Portfolio Performance Server

Exposes Portfolio Performance XML data through MCP tools for AI agents.
"""

import os
from pathlib import Path

from fastmcp import FastMCP

from pyfolio_performance import Portfolio, reset
from pyfolio_performance.classSecurity import Security
from pyfolio_performance.classTransaction import Transaction
from pyfolio_performance.classDepot import Depot

mcp = FastMCP("Portfolio Performance")

portfolio: Portfolio | None = None


# =============================================================================
# Helpers
# =============================================================================

def _to_eur(cents: int) -> float:
    return round(cents / 100, 2)


def _price_to_eur(price_value: float) -> float:
    return round(price_value / 100, 2)


def _xml_price_to_eur(raw_price: int) -> float:
    return round(raw_price / 100000000, 2)


def _require_portfolio() -> Portfolio:
    global portfolio
    if portfolio is None:
        raise RuntimeError("No portfolio loaded")
    return portfolio


def _load_portfolio_impl(file_path: str) -> None:
    global portfolio
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    reset()
    portfolio = Portfolio(str(path.absolute()))


_auto_load_error = None
try:
    _load_portfolio_impl(os.environ.get("PORTFOLIO_FILE", "kommer.xml"))
except Exception as e:
    _auto_load_error = str(e)


def _format_transaction(t: Transaction) -> dict:
    depot = t.content.get("depot")
    account = t.content.get("account")
    return {
        "date": str(t.getDate()),
        "type": t.type,
        "value_eur": _to_eur(t.getValue()),
        "shares": round(t.getShares() / 100000000, 4) if t.getShares() else 0,
        "security": t.getSecurity().getName() if t.getSecurity() else None,
        "depot": depot.getName() if depot else None,
        "account": account.name if account else None
    }


def _get_sec_info(sec: Security, shares: float) -> dict:
    price = _price_to_eur(sec.getMostRecentValue())
    return {
        "name": sec.getName(),
        "isin": sec.isin,
        "wkn": sec.wkn,
        "shares": round(shares, 4),
        "current_price_eur": price,
        "total_value_eur": round(price * shares, 2)
    }


def _get_security(name: str) -> Security:
    sec = Security.getSecurityByName(name)
    if sec is None:
        raise ValueError(f"Security not found: {name}")
    return sec


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
    return {"status": "ok", "message": "Portfolio Performance MCP running"}


@mcp.tool
def load_portfolio(file_path: str | None = None) -> dict:
    """Load a Portfolio Performance export file.

    Clears any previously loaded portfolio and loads a new one.
    If no path is given, falls back to PORTFOLIO_FILE env var or "kommer.xml".

    Args:
        file_path: Absolute or relative path to a Portfolio Performance
                   XML export.

    Returns:
        message: confirmation with the loaded filename
    """
    if file_path is None:
        file_path = os.environ.get("PORTFOLIO_FILE", "kommer.xml")
    _load_portfolio_impl(file_path)
    return {"message": f"Loaded: {Path(file_path).name}"}


@mcp.tool
def reload_portfolio() -> dict:
    """Reload the current portfolio from disk without restarting the server.

    Useful after the source file has been updated externally.
    Requires a portfolio to be loaded first.

    Returns:
        message: confirmation with the reloaded filename
    """
    _require_portfolio()
    file_path = os.environ.get("PORTFOLIO_FILE", "kommer.xml")
    _load_portfolio_impl(file_path)
    return {"message": f"Reloaded: {Path(file_path).name}"}


@mcp.tool
def get_portfolio_summary() -> dict:
    """Quick financial overview — total assets, cash, depot value, and P/L.

    Notes on interpretation:
    - total_payin_eur counts ONLY DEPOSIT, TRANSFER_IN, REMOVAL, TRANSFER_OUT.
      Dividends, interest, tax refunds, and fees are not pay-in. As a
      consequence, profit_loss_eur (= total_assets_eur - total_payin_eur)
      is NOT pure capital gain — it also includes accumulated dividends,
      interest, and FX effects.
    - Cash balances are summed in each account's native currency without
      FX conversion. The "_eur" suffix is a label; verify all accounts are
      EUR via get_accounts() if in doubt.
    - Cash held outside Portfolio Performance (e.g. separate savings
      accounts not tracked here) is NOT included.

    Returns:
        total_cash_eur: sum of all account balances (no FX conversion)
        depot_value_eur: sum of holdings at current market price
        total_assets_eur: total_cash_eur + depot_value_eur
        total_payin_eur: DEPOSIT + TRANSFER_IN - REMOVAL - TRANSFER_OUT
        profit_loss_eur: total_assets_eur - total_payin_eur
        account_count: number of accounts
        depot_count: number of depots
        security_count: number of unique securities held
        accounts: list of {name, balance_eur}
        depots: list of {name, value_eur, invested_eur, profit_eur,
                securities_count, securities: {name: {isin, wkn, shares,
                current_price_eur, total_value_eur}}}
    """
    portfolio = _require_portfolio()

    total_cash_eur = _to_eur(sum(a.getBalance() for a in portfolio.getAccounts()))

    holding_types = ('BUY', 'SELL')

    depot_value = 0
    depot_details = []
    for d in portfolio.getDepots():
        dv = 0
        securities_count = 0
        securities_dict = {}
        for sec, shares in d.getSecurities().items():
            info = _get_sec_info(sec, shares)
            dv += info["total_value_eur"]
            securities_count += 1
            securities_dict[sec.getName()] = info
        dv = round(dv, 2)
        depot_value += dv

        net = sum(t.getValue() for t in d.getTransactions()
                  if t.type in holding_types)
        invested_eur = _to_eur(-net)

        depot_details.append({
            "name": d.getName(),
            "value_eur": dv,
            "invested_eur": invested_eur,
            "profit_eur": round(dv - invested_eur, 2),
            "securities_count": securities_count,
            "securities": securities_dict
        })
    depot_value_eur = round(depot_value, 2)

    net_payin = 0
    for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL):
        if t.type in ('DEPOSIT', 'TRANSFER_IN', 'REMOVAL', 'TRANSFER_OUT'):
            net_payin += t.getValue()
    net_payin_eur = _to_eur(net_payin)

    total_assets_eur = round(total_cash_eur + depot_value_eur, 2)

    return {
        "total_cash_eur": total_cash_eur,
        "depot_value_eur": depot_value_eur,
        "total_assets_eur": total_assets_eur,
        "total_payin_eur": net_payin_eur,
        "profit_loss_eur": round(total_assets_eur - net_payin_eur, 2),
        "account_count": len(portfolio.getAccounts()),
        "depot_count": len(portfolio.getDepots()),
        "security_count": len(portfolio.getSecurities()),
        "accounts": [{"name": a.getName(), "balance_eur": _to_eur(a.getBalance())}
                     for a in portfolio.getAccounts()],
        "depots": depot_details
    }


@mcp.tool
def get_accounts() -> dict:
    """List all accounts with their current cash balances.

    Accounts represent cash holdings (e.g. checking account, deposit account).
    Balances are in each account's native currency — no FX conversion is
    performed. The "_eur" suffix is a label; if you suspect non-EUR
    accounts, the user should verify their setup.

    Returns:
        accounts: list of {name, balance_eur}
    """
    portfolio = _require_portfolio()
    accounts = [{"name": a.getName(), "balance_eur": _to_eur(a.getBalance())}
                for a in portfolio.getAccounts()]
    return {"accounts": accounts}


@mcp.tool
def get_depots() -> dict:
    """List all depots with their security holdings.

    Depots represent brokerage accounts holding securities.
    Each depot includes its securities with current price, shares, and total value.

    Returns:
        depots: list of {name, securities: {security_name: {name, isin, wkn, shares, current_price_eur, total_value_eur}}, transaction_count}
    """
    portfolio = _require_portfolio()
    depots = []
    for depot in portfolio.getDepots():
        securities = {sec.getName(): _get_sec_info(sec, shares)
                      for sec, shares in depot.getSecurities().items()}
        depots.append({"name": depot.getName(), "securities": securities,
                       "transaction_count": len(depot.getTransactions())})
    return {"depots": depots}


@mcp.tool
def get_securities() -> dict:
    """List all securities tracked in the portfolio.

    Includes securities the user has fully sold (shares == 0) and
    watchlist entries that were never bought. For currently held
    positions only, use get_securities_with_values().

    Each entry includes identifying info (ISIN, WKN), current market price,
    total shares held, and total value.

    Returns:
        securities: list of {name, isin, wkn, shares, current_price_eur, total_value_eur}
    """
    portfolio = _require_portfolio()
    securities = [_get_sec_info(sec, portfolio.getShares(sec))
                  for sec in portfolio.getSecurities()]
    return {"securities": securities}


@mcp.tool
def get_transactions() -> dict:
    """Return every transaction in the portfolio (buy, sell, dividend, deposit, etc.).

    Each transaction includes date, type, value in EUR, shares traded,
    the security involved, the depot it was booked in, and the account.

    Returns:
        transactions: list of {date, type, value_eur, shares, security, depot, account}
        count: total number of transactions
    """
    portfolio = _require_portfolio()
    transactions = [_format_transaction(t)
                   for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)]
    return {"transactions": transactions, "count": len(transactions)}


@mcp.tool
def get_account_by_name(name: str) -> dict:
    """Look up a single account by its name (case-insensitive).

    Args:
        name: account name to search for

    Returns:
        account: {name, balance_eur}
    """
    portfolio = _require_portfolio()
    for acc in portfolio.getAccounts():
        if acc.getName().lower() == name.lower():
            return {"account": {"name": acc.getName(),
                                "balance_eur": _to_eur(acc.getBalance())}}
    raise ValueError(f"Account not found: {name}")


@mcp.tool
def get_depot_by_name(name: str) -> dict:
    """Look up a single depot by its name (case-insensitive).

    Args:
        name: depot name to search for

    Returns:
        depot: {name, securities: {security_name: {name, shares, current_price_eur}}}
    """
    portfolio = _require_portfolio()
    for depot in portfolio.getDepots():
        if depot.getName().lower() == name.lower():
            securities = {sec.getName(): {"shares": round(shares, 4),
                                          "current_price_eur": _price_to_eur(sec.getMostRecentValue())}
                         for sec, shares in depot.getSecurities().items()}
            return {"depot": {"name": depot.getName(), "securities": securities}}
    raise ValueError(f"Depot not found: {name}")


@mcp.tool
def get_security_by_name(name: str) -> dict:
    """Look up a security by its name.

    Args:
        name: security name (e.g. "Apple Inc.", "iShares Core MSCI World UCITS ETF")

    Returns:
        security: {name, isin, wkn, shares, current_price_eur, total_value_eur}
    """
    _require_portfolio()
    sec = _get_security(name)
    return {"security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_by_isin(isin: str) -> dict:
    """Look up a security by its ISIN (International Securities Identification Number).

    Args:
        isin: 12-character ISIN code (e.g. "US0378331005" for Apple)

    Returns:
        security: {name, isin, wkn, shares, current_price_eur, total_value_eur}
    """
    _require_portfolio()
    sec = Security.getSecurityByIsin(isin)
    if sec is None:
        raise ValueError(f"Security not found: {isin}")
    return {"security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_by_wkn(wkn: str) -> dict:
    """Look up a security by its WKN (German securities identifier).

    Args:
        wkn: 6-character WKN code (e.g. "865985" for Apple)

    Returns:
        security: {name, isin, wkn, shares, current_price_eur, total_value_eur}
    """
    _require_portfolio()
    sec = Security.getSecurityByWkn(wkn)
    if sec is None:
        raise ValueError(f"Security not found: {wkn}")
    return {"security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_price_history(name: str, limit: int = 100) -> dict:
    """Retrieve historical daily closing prices for a security.

    Prices are returned sorted newest-first.

    Args:
        name: security name
        limit: max number of price entries to return (default 100)

    Returns:
        security: security name
        prices: list of {date, price_eur} sorted by date descending
        count: number of prices returned
        total_available: total number of price records available
    """
    _require_portfolio()
    sec = _get_security(name)

    prices = sec.data.get("prices")
    if prices is None:
        raise ValueError(f"No price history: {name}")

    price_list = prices.get("price")
    if price_list is None:
        raise ValueError(f"No price history: {name}")

    if isinstance(price_list, dict):
        price_list = [price_list]

    history = [{"date": p["@t"], "price_eur": _xml_price_to_eur(int(p["@v"]))}
               for p in price_list if isinstance(p, dict)]
    history.sort(key=lambda x: x["date"], reverse=True)

    return {"security": name, "prices": history[:limit],
            "count": len(history[:limit]), "total_available": len(history)}


@mcp.tool
def get_transactions_by_type(transaction_type: str) -> dict:
    """Filter transactions by type.

    Common types: BUY, SELL, DIVIDENDS, DEPOSIT, REMOVAL, TRANSFER_IN,
    TRANSFER_OUT, INTEREST, INTEREST_CHARGE, FEES, FEES_REFUND, DELIVERY_INBOUND,
    DELIVERY_OUTBOUND, TAXES, TAX_REFUND.

    Args:
        transaction_type: type string (case-insensitive, e.g. "dividends" or "DIVIDENDS")

    Returns:
        transactions: list of matching {date, type, value_eur, shares, security, depot, account}
        count: number of matching transactions
        type: normalized uppercase type
    """
    portfolio = _require_portfolio()
    transactions = [_format_transaction(t) for t in
                   portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)
                   if t.type == transaction_type.upper()]
    return {"transactions": transactions, "count": len(transactions),
            "type": transaction_type.upper()}


@mcp.tool
def get_transactions_by_year(year: int) -> dict:
    """Filter transactions by calendar year.

    Args:
        year: four-digit year (e.g. 2024)

    Returns:
        transactions: list of matching {date, type, value_eur, shares, security, depot, account}
        count: number of matching transactions
        year: the year requested
    """
    portfolio = _require_portfolio()
    transactions = [_format_transaction(t) for t in
                   portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)
                   if t.getYear() == year]
    return {"transactions": transactions, "count": len(transactions), "year": year}


@mcp.tool
def get_transactions_for_security(security_name: str, depot: str | None = None, type: str | None = None) -> dict:
    """Get transactions involving a specific security, optionally filtered by depot and/or type.

    Args:
        security_name: name of the security
        depot: optional depot name to filter by (case-insensitive, matches
               the transaction's depot or account field). Note: dividends,
               deposits, and other account-level transactions won't match
               a depot filter — they are booked to an account instead.
        type: optional transaction type filter (case-insensitive, e.g.
              "dividends", "buy", "sell"). Common values: BUY, SELL,
              DIVIDENDS, DEPOSIT, REMOVAL, TAXES, FEES, DELIVERY_INBOUND,
              DELIVERY_OUTBOUND, TRANSFER_IN, TRANSFER_OUT.

    Returns:
        transactions: list of matching {date, type, value_eur, shares, security, depot, account}
        count: number of matching transactions
        security: the security name queried
        depot: the depot filter applied (if any)
        type: the type filter applied (if any)
    """
    portfolio = _require_portfolio()
    sec = _get_security(security_name)

    filtered = []
    for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL):
        if t.getSecurity() != sec:
            continue
        if type and t.type != type.upper():
            continue
        if depot:
            d = t.content.get("depot")
            a = t.content.get("account")
            name = d.getName() if d else (a.name if a else None)
            if not name or name.lower() != depot.lower():
                continue
        filtered.append(_format_transaction(t))

    result = {
        "transactions": filtered,
        "count": len(filtered),
        "security": security_name
    }
    if depot:
        result["depot"] = depot
    if type:
        result["type"] = type.upper()
    return result


@mcp.tool
def get_securities_with_values() -> dict:
    """List all currently held securities (shares > 0) with current market values.

    Results are sorted by total_value_eur descending (largest holdings first).

    Returns:
        securities: list of {name, shares, current_price_eur, total_value_eur}
        total_value_eur: summed value of all holdings
        count: number of securities with positive share count
    """
    portfolio = _require_portfolio()
    securities = []
    total_value = 0

    for sec in portfolio.getSecurities():
        shares = portfolio.getShares(sec)
        if shares <= 0:
            continue
        price = _price_to_eur(sec.getMostRecentValue())
        value = price * shares
        total_value += value
        securities.append({"name": sec.getName(), "shares": round(shares, 4),
                           "current_price_eur": price, "total_value_eur": round(value, 2)})

    securities.sort(key=lambda x: x["total_value_eur"], reverse=True)
    return {"securities": securities, "total_value_eur": round(total_value, 2),
            "count": len(securities)}


@mcp.tool
def get_performance_by_year() -> dict:
    """Yearly aggregation of all transactions grouped by type.

    Useful for seeing how much was invested, withdrawn, or earned in dividends
    per year. Values are in EUR.

    Returns:
        performance: dict mapping year strings to {transaction_type: total_eur, ...}
                     e.g. {"2024": {"BUY": -5000.0, "DIVIDENDS": 120.0, "DEPOSIT": 6000.0}}
    """
    portfolio = _require_portfolio()
    yearly_data = {}
    for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL):
        year = t.getYear()
        if year not in yearly_data:
            yearly_data[year] = {}
        trans_type = t.type
        yearly_data[year][trans_type] = yearly_data[year].get(trans_type, 0) + t.getValue()

    result = {str(year): {t: _to_eur(val) for t, val in types.items()}
              for year, types in sorted(yearly_data.items())}
    return {"performance": result}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"Portfolio Performance MCP - using {os.environ.get('PORTFOLIO_FILE', 'kommer.xml')}")
    if _auto_load_error:
        print(f"Auto-load error: {_auto_load_error}")
    else:
        print("Auto-load: OK")
    mcp.run()
