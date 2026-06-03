# pyfolio-performance

Python library + MCP server to read Portfolio Performance XML files. Access your portfolio data via AI agents for investment analysis.

## Features

- Parse Portfolio Performance XML export files
- Access accounts, depots, securities, transactions
- MCP server for AI agents (Claude Desktop, Cursor, OpenCode, kiro-cli)
- Price history tracking

## Local Development

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

Run the regression tests:

```bash
python -m pytest
ruff check .
```

## Portfolio Performance MCP Server

This project includes an MCP (Model Context Protocol) server that exposes your Portfolio Performance data to AI agents for investment analysis and advice.

### Quick Setup (native with pyenv/venv)

```bash
# 1. Use Python 3.12 via pyenv, then create and activate virtual environment
pyenv install 3.12  # if needed
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test the server
python mcp_server.py
```

The devcontainer uses `.venv-devcontainer` instead. Activate the matching venv
before starting `opencode`, because MCP commands use plain `python`.

### Configuration

The server auto-loads the portfolio on startup from:
1. `PORTFOLIO_FILE` environment variable
2. Defaults to `kommer.xml` in project root

### Available Tools

| Tool | Description |
|------|-------------|
| `ping` | Health check — verify server is running |
| `load_portfolio` | Load a portfolio XML file |
| `reload_portfolio` | Reload current portfolio without restart |
| `get_portfolio_summary` | Full overview: cash, depot values, P/L, per-account and per-depot breakdowns with invested/profit and full holdings |
| `get_accounts` | All accounts with cash balances |
| `get_account_by_name` | Single account by name |
| `get_depots` | All depots with full security holdings |
| `get_depot_by_name` | Single depot by name |
| `get_securities` | All securities with ISIN, WKN, price, value, ticker, currency, custom attributes |
| `get_transactions` | All transactions with depot and account info |
| `get_transactions_by_type` | Filter by type (BUY, SELL, DIVIDENDS, etc.) |
| `get_transactions_by_year` | Filter by year |
| `get_transactions_for_security` | Filter by security, optionally by depot and type |
| `get_security_by_name` / `by_isin` / `by_wkn` | Look up a security |
| `get_security_price_history` | Historical daily closing prices |
| `get_performance_by_year` | Yearly totals grouped by transaction type |

### OpenCode Integration

Add this to your project `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "portfolio": {
      "type": "local",
      "command": ["python", "mcp_server.py"],
      "environment": {
        "PORTFOLIO_FILE": "kommer.xml"
      },
      "enabled": true
    }
  }
}
```

Then activate the native `.venv` or container `.venv-devcontainer` and run
opencode from the project directory. The portfolio auto-loads on startup.

## ExtraETF MCP Server

A lightweight MCP server that fetches ETF holdings, factsheets, allocations, and dividend data from [extraetf.com](https://extraetf.com). No API key needed — data is extracted from the ETF profile page.

### Tools

| Tool | Description |
|------|-------------|
| `get_etf_holdings` | Top holdings with ISIN, weight, sector, country |
| `get_etf_factsheet` | TER, fund size, replication, performance, risk metrics |
| `get_etf_allocation` | Country, region, sector, currency, asset class breakdown |
| `get_etf_dividends` | Dividend history, yields, CAGR |
| `ping` | Health check |

### OpenCode Integration

Add a second MCP server to `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "portfolio": { ... },
    "extraetf": {
      "type": "local",
      "command": ["./venv/bin/python", "extraetf_server.py"],
      "enabled": true
    }
  }
}
```

## yfinance MCP server

[yfinance](https://github.com/narumiruna/yfinance-mcp) pairs well with this project — get prices, fundamentals, and news for individual stocks alongside your portfolio and ETF data.

```
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "yfinance": {
      "type": "local",
      "command": ["docker", "run", "-i", "--rm", "narumi/yfinance-mcp"],
      "enabled": true
    }
  }
}
```

## Sample Prompt


```
You are a portfolio analyst. Analyze this portfolio across:
- Strategy clarity
- Portfolio structure & diversification
- Position quality & redundancies
- Risk analysis (sector, regional, career correlation)
- Performance overview
- Concrete recommendations & target portfolio
- Scenario forecasts (conservative/realistic/optimistic)
- Market valuation & phase
- Holistic wealth perspective
- Financial independence timeline
- Complexity & robustness scores (KPI)
- Long-term sustainability

Use the MCP tools to fetch data, then provide actionable insights.
```

## Tests

The test suite includes small XML fixtures copied from the upstream Portfolio
Performance project under `tests/fixtures/original_project/`. They cover account
balances, depot holdings, tax/fee transactions, delivery transactions,
portfolio transfers, single-node XML parsing, and class-level cache resets.

Run:

```bash
python -m pytest
ruff check .
```

`*.xml` files are ignored by default to avoid committing personal portfolio data.
Only the public fixture XML files under `tests/fixtures/original_project/` are
explicitly unignored.

## Docs

https://pyfolio-performance.readthedocs.io/en/latest/

## Changelog

See [FIXES.md](FIXES.md) for a record of bugs fixed in this fork.
