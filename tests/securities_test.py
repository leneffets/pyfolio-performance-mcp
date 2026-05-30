from pathlib import Path

from pyfolio_performance import Portfolio, Security


def test_mostrecentvalue() -> None:
    security = Security.get_security_by_isin("DE0005190003")
    if security is not None:
        security.get_most_recent_value()
    assert True


def test_loaded_portfolio_depot_securities(tmp_path: Path) -> None:
    portfolio_file = tmp_path / "portfolio.xml"
    portfolio_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<client>
  <securities>
    <security>
      <name>Test ETF</name>
      <currencyCode>EUR</currencyCode>
    </security>
  </securities>
  <portfolios>
    <portfolio>
      <name>Test Depot</name>
      <uuid>depot-1</uuid>
      <transactions>
        <portfolio-transaction>
          <uuid>transaction-1</uuid>
          <date>2024-01-01T00:00</date>
          <currencyCode>EUR</currencyCode>
          <type>BUY</type>
          <amount>10000</amount>
          <shares>100000000</shares>
          <security reference="../securities/security" />
        </portfolio-transaction>
      </transactions>
    </portfolio>
  </portfolios>
</client>
""",
        encoding="utf-8",
    )

    portfolio = Portfolio(str(portfolio_file))
    depot = portfolio.get_depots()[0]

    securities = depot.get_securities()

    assert {security.get_name(): shares for security, shares in securities.items()} == {
        "Test ETF": 1,
    }
