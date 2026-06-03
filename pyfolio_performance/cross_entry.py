from __future__ import annotations

from typing import Any

from .portfolio_performance_object import PortfolioPerformanceObject


class CrossEntry(PortfolioPerformanceObject):
    cross_entry_queue: list[Any] = []

    @staticmethod
    def process_cross_entries() -> None:
        while len(CrossEntry.cross_entry_queue) > 0:
            next_entry = CrossEntry.cross_entry_queue.pop()

            if next_entry.content["@class"] == "portfolio-transfer":
                CrossEntry.cross_entry_portfolio_transfer(next_entry)
            elif next_entry.content["@class"] == "buysell":
                CrossEntry.cross_entry_buysell(next_entry)
            elif next_entry.content["@class"] == "account-transfer":
                CrossEntry.cross_entry_account_transfer(next_entry)

    @staticmethod
    def cross_entry_buysell(next_entry: Any) -> None:
        other_depot = next_entry.content["portfolio"]
        transaction = next_entry.content["portfolioTransaction"]
        if other_depot is None or transaction is None:
            return
        if transaction.reference is not None:
            return

        other_depot.resolve_reference()
        transaction.resolve_reference()
        other_depot.transactions.append(transaction)

    @staticmethod
    def cross_entry_portfolio_transfer(next_entry: Any) -> None:
        other_depot = next_entry.content["portfolioFrom"]
        transaction_from = next_entry.content["transactionFrom"]
        if other_depot is None or transaction_from is None:
            return

        other_depot.resolve_reference()
        transaction_from.resolve_reference()
        other_depot.transactions.append(transaction_from)

    @staticmethod
    def cross_entry_account_transfer(next_entry: Any) -> None:
        account_from = next_entry.content.get("accountFrom")
        account_to = next_entry.content.get("accountTo")
        tx_from = next_entry.content.get("transactionFrom")
        tx_to = next_entry.content.get("transactionTo")

        def _already_exists(tx: Any, account: Any) -> bool:
            new_uuid = tx.content.get("uuid") if hasattr(tx, "content") else None
            if new_uuid:
                for existing in account.transactions:
                    if existing.content.get("uuid") == new_uuid:
                        return True
                return False

            for existing in account.transactions:
                if (
                    existing.get_date().get_order_value() == tx.get_date().get_order_value()
                    and existing.type == tx.type
                    and existing.get_value() == tx.get_value()
                ):
                    return True
            return False

        if account_from and tx_from:
            account_from.resolve_reference()
            tx_from.resolve_reference()
            if not _already_exists(tx_from, account_from):
                account_from.transactions.append(tx_from)

        if account_to and tx_to:
            account_to.resolve_reference()
            tx_to.resolve_reference()
            if not _already_exists(tx_to, account_to):
                account_to.transactions.append(tx_to)

    @staticmethod
    def parse(content: Any) -> CrossEntry | None:  # type: ignore[override]
        from .account import Account  # noqa: PLC0415
        from .depot import Depot  # noqa: PLC0415
        from .transaction import Transaction  # noqa: PLC0415

        if "@reference" in content:
            return None

        if "portfolio" in content:
            content["portfolio"]["referencePath"] = content["referencePath"] + "/portfolio"
            content["portfolio"] = Depot.parse(content["portfolio"])
        if "account" in content:
            content["account"]["referencePath"] = content["referencePath"] + "/account"
            content["account"] = Account.parse(content["account"])
        if "accountFrom" in content:
            content["accountFrom"]["referencePath"] = content["referencePath"] + "/accountFrom"
            content["accountFrom"] = Account.parse(content["accountFrom"])
        if "accountTo" in content:
            content["accountTo"]["referencePath"] = content["referencePath"] + "/accountTo"
            content["accountTo"] = Account.parse(content["accountTo"])
        if "portfolioTo" in content:
            content["portfolioTo"]["referencePath"] = content["referencePath"] + "/portfolioTo"
            content["portfolioTo"] = Depot.parse(content["portfolioTo"])
        if "portfolioFrom" in content:
            content["portfolioFrom"]["referencePath"] = content["referencePath"] + "/portfolioFrom"
            content["portfolioFrom"] = Depot.parse(content["portfolioFrom"])

        if "accountTransaction" in content:
            content["accountTransaction"]["referencePath"] = (
                content["referencePath"] + "/accountTransaction"
            )
            content["accountTransaction"]["account"] = content["account"]
            content["accountTransaction"] = Transaction.parse(content["accountTransaction"])
        if "transactionFrom" in content:
            content["transactionFrom"]["referencePath"] = (
                content["referencePath"] + "/transactionFrom"
            )
            content["transactionFrom"]["account"] = content.get("accountFrom", None)
            content["transactionFrom"] = Transaction.parse(content["transactionFrom"])
        if "transactionTo" in content:
            content["transactionTo"]["referencePath"] = content["referencePath"] + "/transactionTo"
            content["transactionTo"]["account"] = content.get("accountTo", None)
            content["transactionTo"] = Transaction.parse(content["transactionTo"])
        if "portfolioTransaction" in content:
            content["portfolioTransaction"]["referencePath"] = (
                content["referencePath"] + "/portfolioTransaction"
            )
            content["portfolioTransaction"] = Transaction.parse(content["portfolioTransaction"])

        cross_entry = CrossEntry(content)
        CrossEntry.cross_entry_queue.append(cross_entry)
        return cross_entry

    def __init__(self, content: Any) -> None:
        self.content = content
