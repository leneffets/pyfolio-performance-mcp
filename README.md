# pyfolio-performance

Python library + MCP server to read Portfolio Performance XML files. Access your portfolio data via AI agents for investment analysis.

## Features

- Parse Portfolio Performance XML export files
- Access accounts, depots, securities, transactions
- MCP server for AI agents (Claude Desktop, Cursor, OpenCode, kiro-cli)
- Price history tracking

## Installation

```bash
pip install pyfolio-performance
```

## Local Development

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Test
python -c "
from pyfolio_performance import Portfolio, reset

reset()
port_perf = Portfolio('your_file.xml')

total_in = sum(a.get_balance() for a in port_perf.get_accounts())
depot_value = sum(sec.get_most_recent_value() * shares 
                   for d in port_perf.get_depots() 
                   for sec, shares in d.get_securities().items())

print(f'Pay-in: {total_in/100:.2f} EUR')
print(f'Depot: {depot_value/100:.2f} EUR')
print(f'P/L: {(depot_value-total_in)/100:.2f} EUR')
"
```

## Quick Start

```python
from pyfolio_performance import Portfolio, reset

reset()  # clear any previous state
port_perf = Portfolio('your_file.xml')

# Get accounts and depots
for account in port_perf.get_accounts():
    print(f"{account.get_name()}: {account.get_balance()/100} EUR")

for depot in port_perf.get_depots():
    for sec, shares in depot.get_securities().items():
        print(f"{sec.get_name()}: {shares} shares @ {sec.get_most_recent_value()/100} EUR")
```

## MCP Server

This project includes an MCP (Model Context Protocol) server that exposes your Portfolio Performance data to AI agents for investment analysis and advice.

### Quick Setup (with venv)

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test the server
python mcp_server.py
```

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
      "command": ["./venv/bin/python", "mcp_server.py"],
      "environment": {
        "PORTFOLIO_FILE": "kommer.xml"
      },
      "enabled": true
    }
  }
}
```

Then run opencode from the project directory. The portfolio auto-loads on startup.

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

## Test Files

- **Official test file:** https://github.com/portfolio-performance/portfolio/blob/master/name.abuchen.portfolio.ui/src/name/abuchen/portfolio/ui/parts/kommer.xml

## Docs

https://pyfolio-performance.readthedocs.io/en/latest/

## Changelog

See [FIXES.md](FIXES.md) for a record of bugs fixed in this fork.