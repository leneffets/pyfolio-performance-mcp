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
portPerf = Portfolio('your_file.xml')

total_in = sum(a.getBalance() for a in portPerf.getAccounts())
depot_value = sum(sec.getMostRecentValue() * shares 
                   for d in portPerf.getDepots() 
                   for sec, shares in d.getSecurities().items())

print(f'Pay-in: {total_in/100:.2f} EUR')
print(f'Depot: {depot_value/100:.2f} EUR')
print(f'P/L: {(depot_value-total_in)/100:.2f} EUR')
"
```

## Quick Start

```python
from pyfolio_performance import Portfolio, reset

reset()  # clear any previous state
portPerf = Portfolio('your_file.xml')

# Get accounts and depots
for account in portPerf.getAccounts():
    print(f"{account.getName()}: {account.getBalance()/100} EUR")

for depot in portPerf.getDepots():
    for sec, shares in depot.getSecurities().items():
        print(f"{sec.getName()}: {shares} shares @ {sec.getMostRecentValue()/100} EUR")
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
| `ping` | Health check - verify server is running |
| `load_portfolio` | Load a portfolio XML file |
| `reload_portfolio` | Reload current portfolio without restart |
| `get_portfolio_summary` | Quick overview: total value, P/L, counts |
| `get_accounts` | All accounts with balances |
| `get_depots` | All depots with securities |
| `get_securities` | All securities in portfolio |
| `get_all_transactions` | All transactions |
| `get_account_by_name` | Single account by name |
| `get_depot_by_name` | Single depot by name |
| `get_security_by_name` | Find security by name |
| `get_security_by_isin` | Find security by ISIN |
| `get_security_by_wkn` | Find security by WKN |
| `get_transactions_by_type` | Filter by type (BUY, SELL, DIVIDENDS, etc.) |
| `get_transactions_by_year` | Filter by year |
| `get_transactions_for_security` | All trades for a security |
| `get_securities_with_values` | Securities with current values |
| `get_performance_by_year` | Yearly totals by transaction type |
| `get_security_price_history` | Historical price data for a security |

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

## Test Files

- **Official test file:** https://github.com/portfolio-performance/portfolio/blob/master/name.abuchen.portfolio.ui/src/name/abuchen/portfolio/ui/parts/kommer.xml

## Docs

https://pyfolio-performance.readthedocs.io/en/latest/