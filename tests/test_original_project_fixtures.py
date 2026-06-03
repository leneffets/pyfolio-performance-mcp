from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pytest

from pyfolio_performance import Portfolio, Security

FIXTURES = Path(__file__).parent / "fixtures" / "original_project"


def load_fixture(path: Path) -> Portfolio:
    return Portfolio(str(path))


def transaction_counts(portfolio: Portfolio, scope: str) -> dict[str, int]:
    transactions = portfolio.get_total_transactions(scope)
    return dict(Counter(transaction.type for transaction in transactions))


def transaction_totals(portfolio: Portfolio, scope: str) -> dict[str, int | float]:
    totals: defaultdict[str, int | float] = defaultdict(int)
    for transaction in portfolio.get_total_transactions(scope):
        totals[transaction.type] += transaction.get_value()
    return dict(totals)


def holdings(portfolio: Portfolio) -> dict[str, dict[str, float]]:
    return {
        depot.get_name(): {
            security.get_name(): shares
            for security, shares in depot.get_securities().items()
        }
        for depot in portfolio.get_depots()
    }


def account_balances(portfolio: Portfolio) -> dict[str, int]:
    return {
        account.get_name(): account.get_balance()
        for account in portfolio.get_accounts()
    }


@pytest.mark.parametrize(
    ("fixture", "expected_balance", "expected_totals"),
    [
        (
            FIXTURES / "account_performance_tax_refund.xml",
            {"Account A": 990000},
            {
                "DEPOSIT": 1000000,
                "TAXES": -20000,
                "TAX_REFUND": 10000,
            },
        ),
        (
            FIXTURES / "security_tax_and_fee_account_transactions.xml",
            {"Account": 844200},
            {
                "BUY": -153300,
                "DEPOSIT": 1000000,
                "FEES": -1000,
                "FEES_REFUND": 500,
                "TAXES": -2500,
                "TAX_REFUND": 500,
            },
        ),
    ],
)
def test_account_transaction_signs_and_balances(
    fixture: Path,
    expected_balance: dict[str, int],
    expected_totals: dict[str, int],
) -> None:
    portfolio = load_fixture(fixture)

    assert account_balances(portfolio) == expected_balance
    assert transaction_totals(portfolio, Portfolio.TRANSACTION_ACCOUNT) == expected_totals


def test_security_tax_and_fee_fixture_deduplicates_buy_in_all_transactions() -> None:
    portfolio = load_fixture(FIXTURES / "security_tax_and_fee_account_transactions.xml")

    assert transaction_counts(portfolio, Portfolio.TRANSACTION_ACCOUNT) == {
        "BUY": 1,
        "DEPOSIT": 1,
        "FEES": 1,
        "FEES_REFUND": 1,
        "TAXES": 1,
        "TAX_REFUND": 1,
    }
    assert transaction_counts(portfolio, Portfolio.TRANSACTION_DEPOT) == {"BUY": 1}
    assert transaction_counts(portfolio, Portfolio.TRANSACTION_ALL) == {
        "BUY": 1,
        "DEPOSIT": 1,
        "FEES": 1,
        "FEES_REFUND": 1,
        "TAXES": 1,
        "TAX_REFUND": 1,
    }
    assert holdings(portfolio) == {"Portfolio": {"Adidas AG": 0.1}}


@pytest.mark.parametrize(
    ("fixture", "expected_holdings", "expected_totals"),
    [
        (
            FIXTURES / "security_performance_tax_refund.xml",
            {"Portfolio A": {"Basf SE": 0.1}},
            {
                "DELIVERY_INBOUND": 765800,
                "TAX_REFUND": 500,
            },
        ),
        (
            FIXTURES / "security_performance_tax_refund_all_sold.xml",
            {"Portfolio A": {}},
            {
                "DELIVERY_INBOUND": 765800,
                "SELL": 741000,
                "TAX_REFUND": 500,
            },
        ),
    ],
)
def test_delivery_and_sell_transactions_use_xml_amounts(
    fixture: Path,
    expected_holdings: dict[str, dict[str, float]],
    expected_totals: dict[str, int],
) -> None:
    portfolio = load_fixture(fixture)

    assert holdings(portfolio) == expected_holdings
    assert transaction_totals(portfolio, Portfolio.TRANSACTION_ALL) == expected_totals


def test_portfolio_transfer_cross_entries_attach_counterparty_transactions() -> None:
    portfolio = load_fixture(FIXTURES / "Issue1898TradeIRRwithPortfolioTransfers.xml")

    assert account_balances(portfolio) == {
        "Referenz 1": 0,
        "Referenz 2": 1306857,
    }
    assert holdings(portfolio) == {
        "Depot 1": {},
        "Depot 2": {"MASCH. BERTH. HERMLE AG Inhaber": 0.25},
    }
    assert transaction_counts(portfolio, Portfolio.TRANSACTION_DEPOT) == {
        "BUY": 2,
        "SELL": 1,
        "TRANSFER_IN": 1,
        "TRANSFER_OUT": 1,
    }
    assert transaction_totals(portfolio, Portfolio.TRANSACTION_DEPOT) == {
        "BUY": -1211415,
        "SELL": 1306857,
        "TRANSFER_IN": 1160500,
        "TRANSFER_OUT": -1160500,
    }


def test_multiple_portfolio_transfers_keep_distinct_same_type_entries() -> None:
    portfolio = load_fixture(FIXTURES / "Issue4446FIFOMultipleTransfers.xml")

    assert holdings(portfolio) == {
        "Depot 1": {},
        "Depot 2": {},
        "Depot 3": {"ADIDAS AG NA O.N.": 10.0},
        "Depot 4": {},
    }
    assert transaction_counts(portfolio, Portfolio.TRANSACTION_DEPOT) == {
        "BUY": 4,
        "SELL": 1,
        "TRANSFER_IN": 3,
        "TRANSFER_OUT": 3,
    }
    assert transaction_totals(portfolio, Portfolio.TRANSACTION_DEPOT) == {
        "BUY": -300000,
        "SELL": 300000,
        "TRANSFER_IN": 600000,
        "TRANSFER_OUT": -600000,
    }


def test_single_transaction_fileversion_fixture_parses_dict_nodes() -> None:
    portfolio = load_fixture(FIXTURES / "client69.xml")

    assert len(portfolio.get_securities()) == 1
    assert account_balances(portfolio) == {"dividendExdate": 1007}
    assert transaction_counts(portfolio, Portfolio.TRANSACTION_ALL) == {"DIVIDENDS": 1}
    assert transaction_totals(portfolio, Portfolio.TRANSACTION_ALL) == {"DIVIDENDS": 1007}


def test_empty_account_and_depot_nodes_are_valid() -> None:
    portfolio = load_fixture(FIXTURES / "IssueUmarshallingArraysArrayList.xml")

    assert portfolio.get_securities() == []
    assert account_balances(portfolio) == {"asdf": 0}
    assert holdings(portfolio) == {"sadf": {}}
    assert portfolio.get_total_transactions(Portfolio.TRANSACTION_ALL) == []


def test_loading_second_portfolio_resets_global_security_maps() -> None:
    first = load_fixture(FIXTURES / "security_performance_tax_refund.xml")
    assert [security.get_name() for security in first.get_securities()] == ["Basf SE"]
    assert Security.get_security_by_name("Basf SE") is not None

    second = load_fixture(FIXTURES / "IssueUmarshallingArraysArrayList.xml")
    assert second.get_securities() == []
    assert Security.get_security_by_name("Basf SE") is None


def test_security_lookup_and_price_scale_from_original_fixture() -> None:
    portfolio = load_fixture(FIXTURES / "security_tax_and_fee_account_transactions.xml")
    securities: dict[str, Any] = {
        security.get_name(): security
        for security in portfolio.get_securities()
    }

    assert securities["Sap AG"].ticker_symbol == "SAP.DE"
    assert securities["Sap AG"].currency_code == "EUR"
    assert securities["Sap AG"].get_most_recent_value() == pytest.approx(0.8463)
    assert Security.get_security_by_name("Adidas AG") is securities["Adidas AG"]
