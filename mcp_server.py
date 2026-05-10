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
    """Convert cents to EUR (account balances, transaction values)."""
    return round(cents / 100, 2)


def _price_to_eur(price_value: float) -> float:
    """Convert security price from getMostRecentValue() to EUR.
    The lib returns price * 100, so divide by 100."""
    return round(price_value / 100, 2)


def _xml_price_to_eur(raw_price: int) -> float:
    """Convert raw XML price to EUR (stored as price * 100000000)."""
    return round(raw_price / 100000000, 2)


def _load_portfolio_impl(file_path: str) -> dict:
    global portfolio
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        reset()
        portfolio = Portfolio(str(path.absolute()))
        return {"success": True, "message": f"Loaded: {path.name}", "file": str(path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def load_portfolio_from_env() -> dict:
    file_path = os.environ.get("PORTFOLIO_FILE", "kommer.xml")
    return _load_portfolio_impl(file_path)


def _format_transaction(t: Transaction) -> dict:
    return {
        "date": str(t.getDate()),
        "type": t.type,
        "value_eur": _to_eur(t.getValue()),
        "shares": round(t.getShares() / 100000000, 4) if t.getShares() else 0,
        "security": t.getSecurity().getName() if t.getSecurity() else None
    }


def _get_sec_info(sec: Security, shares: float) -> dict:
    """Helper to get security info with current price and total value."""
    price = _price_to_eur(sec.getMostRecentValue())
    return {
        "name": sec.getName(),
        "isin": sec.isin,
        "wkn": sec.wkn,
        "shares": round(shares, 4),
        "current_price_eur": price,
        "total_value_eur": round(price * shares, 2)
    }


# Auto-load portfolio on startup
_auto_load_result = load_portfolio_from_env()


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool
def ping() -> dict:
    """Health check - verify server is running."""
    return {"status": "ok", "message": "Portfolio Performance MCP running"}


@mcp.tool
def load_portfolio(file_path: str | None = None) -> dict:
    """Load a portfolio from an XML file."""
    if file_path is None:
        return load_portfolio_from_env()
    return _load_portfolio_impl(file_path)


@mcp.tool
def reload_portfolio() -> dict:
    """Reload the current portfolio without restart."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}
    return _load_portfolio_impl(os.environ.get("PORTFOLIO_FILE", "kommer.xml"))


@mcp.tool
def get_portfolio_summary() -> dict:
    """Quick overview: total value, P/L, account/depot counts."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    # Account balances (in cents)
    total_in = sum(a.getBalance() for a in portfolio.getAccounts())
    total_in_eur = _to_eur(total_in)

    # Depot values (securities * price)
    depot_value = 0
    for d in portfolio.getDepots():
        for sec, shares in d.getSecurities().items():
            price_eur = _price_to_eur(sec.getMostRecentValue())
            depot_value += price_eur * shares

    return {
        "success": True,
        "total_payin_eur": total_in_eur,
        "depot_value_eur": round(depot_value, 2),
        "profit_loss_eur": round(depot_value - total_in_eur, 2),
        "account_count": len(portfolio.getAccounts()),
        "depot_count": len(portfolio.getDepots()),
        "security_count": len(portfolio.getSecurities())
    }


@mcp.tool
def get_accounts() -> dict:
    """All accounts with balances."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    accounts = [{"name": a.getName(), "balance_eur": _to_eur(a.getBalance())}
                for a in portfolio.getAccounts()]
    return {"success": True, "accounts": accounts}


@mcp.tool
def get_depots() -> dict:
    """All depots with securities."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    depots = []
    for depot in portfolio.getDepots():
        securities = {sec.getName(): _get_sec_info(sec, shares)
                      for sec, shares in depot.getSecurities().items()}
        depots.append({"name": depot.getName(), "securities": securities,
                       "transaction_count": len(depot.getTransactions())})
    return {"success": True, "depots": depots}


@mcp.tool
def get_securities() -> dict:
    """All securities in portfolio."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    securities = [_get_sec_info(sec, portfolio.getShares(sec))
                  for sec in portfolio.getSecurities()]
    return {"success": True, "securities": securities}


@mcp.tool
def get_all_transactions() -> dict:
    """All transactions."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    transactions = [_format_transaction(t)
                   for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)]
    return {"success": True, "transactions": transactions, "count": len(transactions)}


@mcp.tool
def get_account_by_name(name: str) -> dict:
    """Single account by name."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    for acc in portfolio.getAccounts():
        if acc.getName().lower() == name.lower():
            return {"success": True, "account": {"name": acc.getName(),
                                                  "balance_eur": _to_eur(acc.getBalance())}}
    return {"success": False, "error": f"Account not found: {name}"}


@mcp.tool
def get_depot_by_name(name: str) -> dict:
    """Single depot by name."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    for depot in portfolio.getDepots():
        if depot.getName().lower() == name.lower():
            securities = {sec.getName(): {"shares": round(shares, 4),
                                          "current_price_eur": _price_to_eur(sec.getMostRecentValue())}
                         for sec, shares in depot.getSecurities().items()}
            return {"success": True, "depot": {"name": depot.getName(), "securities": securities}}
    return {"success": False, "error": f"Depot not found: {name}"}


@mcp.tool
def get_security_by_name(name: str) -> dict:
    """Find security by name."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    sec = Security.getSecurityByName(name)
    if sec is None:
        return {"success": False, "error": f"Security not found: {name}"}

    return {"success": True, "security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_by_isin(isin: str) -> dict:
    """Find security by ISIN."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    sec = Security.getSecurityByIsin(isin)
    if sec is None:
        return {"success": False, "error": f"Security not found: {isin}"}

    return {"success": True, "security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_by_wkn(wkn: str) -> dict:
    """Find security by WKN."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    sec = Security.getSecurityByWkn(wkn)
    if sec is None:
        return {"success": False, "error": f"Security not found: {wkn}"}

    return {"success": True, "security": _get_sec_info(sec, portfolio.getShares(sec))}


@mcp.tool
def get_security_price_history(name: str, limit: int = 100) -> dict:
    """Historical price data for a security."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    sec = Security.getSecurityByName(name)
    if sec is None:
        return {"success": False, "error": f"Security not found: {name}"}

    prices = sec.data.get("prices")
    if prices is None:
        return {"success": False, "error": f"No price history: {name}"}

    price_list = prices.get("price")
    if price_list is None:
        return {"success": False, "error": f"No price history: {name}"}

    if isinstance(price_list, dict):
        price_list = [price_list]

    history = [{"date": p["@t"], "price_eur": _xml_price_to_eur(int(p["@v"]))}
               for p in price_list if isinstance(p, dict)]
    history.sort(key=lambda x: x["date"], reverse=True)

    return {"success": True, "security": name, "prices": history[:limit],
            "count": len(history[:limit]), "total_available": len(history)}


@mcp.tool
def get_transactions_by_type(transaction_type: str) -> dict:
    """Filter transactions by type (BUY, SELL, DIVIDENDS, etc.)."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    transactions = [_format_transaction(t) for t in
                   portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)
                   if t.type == transaction_type.upper()]
    return {"success": True, "transactions": transactions, "count": len(transactions),
            "type": transaction_type.upper()}


@mcp.tool
def get_transactions_by_year(year: int) -> dict:
    """Filter transactions by year."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    transactions = [_format_transaction(t) for t in
                   portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)
                   if t.getYear() == year]
    return {"success": True, "transactions": transactions, "count": len(transactions), "year": year}


@mcp.tool
def get_transactions_for_security(security_name: str) -> dict:
    """All transactions for a security."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    sec = Security.getSecurityByName(security_name)
    if sec is None:
        return {"success": False, "error": f"Security not found: {security_name}"}

    transactions = [_format_transaction(t) for t in
                   portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL)
                   if t.getSecurity() == sec]
    return {"success": True, "transactions": transactions, "count": len(transactions),
            "security": security_name}


@mcp.tool
def get_securities_with_values() -> dict:
    """Securities with current values (sorted by value)."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

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
    return {"success": True, "securities": securities, "total_value_eur": round(total_value, 2),
            "count": len(securities)}


@mcp.tool
def get_performance_by_year() -> dict:
    """Yearly performance totals by transaction type."""
    global portfolio
    if portfolio is None:
        return {"success": False, "error": "No portfolio loaded"}

    yearly_data = {}
    for t in portfolio.getTotalTransactions(Portfolio.TRANSACTION_ALL):
        year = t.getYear()
        if year not in yearly_data:
            yearly_data[year] = {}
        trans_type = t.type
        yearly_data[year][trans_type] = yearly_data[year].get(trans_type, 0) + t.getValue()

    result = {str(year): {t: _to_eur(val) for t, val in types.items()}
              for year, types in sorted(yearly_data.items())}
    return {"success": True, "performance": result}


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print(f"Portfolio Performance MCP - using {os.environ.get('PORTFOLIO_FILE', 'kommer.xml')}")
    print(f"Auto-load: {_auto_load_result}")
    mcp.run()