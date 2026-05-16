# Python MCP Server — pyfolio-performance

## Project Structure

Root of the Python-based MCP server project. The `portfolio/` subdirectory is a separate Java/RCP project (see its own `AGENTS.md`).

- `mcp_server.py` — FastMCP server exposing Portfolio Performance XML data as MCP tools
- `pyfolio_performance/` — core library (Portfolio, Security, Transaction, Depot, Account classes)
- `opencode.json` — MCP client configuration (used by opencode)
- `requirements.txt` — `xmltodict==1.0.4` + `fastmcp>=3.2.0`
- `venv/` — Python 3.12 virtual environment
- `tests/` — unit tests
- `docs/` — Sphinx documentation

## How to Run

```bash
cd /home/steffen/pyfolio-performance-mcp
./venv/bin/python mcp_server.py
```

The server auto-loads a portfolio from the `PORTFOLIO_FILE` env var or falls back to `kommer.xml`.

## MCP Tools

ping, load_portfolio, reload_portfolio, get_portfolio_summary, get_accounts, get_account_by_name, get_depots, get_depot_by_name, get_securities, get_securities_with_values, get_security_by_name, get_security_by_isin, get_security_by_wkn, get_security_price_history, get_transactions, get_transactions_by_type, get_transactions_by_year, get_transactions_for_security, get_performance_by_year

All tools return `dict`. Patterns: `_require_portfolio()` guard, `_to_eur()` / `_price_to_eur()` helpers, snake_case naming, Google-style docstrings.

## Adding a Tool

Define a function with `@mcp.tool`, type-annotated params, and a docstring. FastMCP auto-generates JSON Schema and handles validation. No manual schema wiring needed.

## OpenCode Config

`opencode.json` registers the server:
```json
{
  "mcp": {
    "portfolio": {
      "type": "local",
      "command": ["./venv/bin/python", "mcp_server.py"],
      "environment": { "PORTFOLIO_FILE": "kommer.xml" },
      "enabled": true
    }
  }
}
```

## Privacy Policy

DO NOT EXPOSE ANY REAL PERSONAL DATA like balances, depots, ages, names, prompt files that may expose data

## Commits

Use conventional commits format when committing changes.