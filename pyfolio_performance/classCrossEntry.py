# ruff: noqa: N802, N803, N806, N815, N999

from __future__ import annotations

from typing import Any

from .classPortfolioPerformanceObject import PortfolioPerformanceObject


class CrossEntry(PortfolioPerformanceObject):
    crossEntryQueue: list[Any] = []

    @staticmethod
    def processCrossEntries() -> None:
        while len(CrossEntry.crossEntryQueue) > 0:
            nextEntry = CrossEntry.crossEntryQueue.pop()

            if nextEntry.content["@class"] == "portfolio-transfer":
                CrossEntry.crossEntry_portfolioTransfer(nextEntry)
            elif nextEntry.content["@class"] == "buysell":
                CrossEntry.crossEntry_buysell(nextEntry)
            elif nextEntry.content["@class"] == "account-transfer":
                CrossEntry.crossEntry_accountTransfer(nextEntry)

    @staticmethod
    def crossEntry_buysell(nextEntry: Any) -> None:
        otherDepot = nextEntry.content["portfolio"]
        transaction = nextEntry.content["portfolioTransaction"]
        if otherDepot is None or transaction is None:
            return
        if transaction.reference is not None:
            return

        otherDepot.resolve_reference()
        transaction.resolve_reference()
        otherDepot.transactions.append(transaction)

    @staticmethod
    def crossEntry_portfolioTransfer(nextEntry: Any) -> None:
        otherDepot = nextEntry.content["portfolioFrom"]
        transactionFrom = nextEntry.content["transactionFrom"]
        if otherDepot is None or transactionFrom is None:
            return

        otherDepot.resolve_reference()
        transactionFrom.resolve_reference()
        otherDepot.transactions.append(transactionFrom)

    @staticmethod
    def crossEntry_accountTransfer(nextEntry: Any) -> None:
        acct_from = nextEntry.content.get("accountFrom")
        acct_to = nextEntry.content.get("accountTo")
        tx_from = nextEntry.content.get("transactionFrom")
        tx_to = nextEntry.content.get("transactionTo")

        def _already_exists(tx: Any, account: Any) -> bool:
            new_uuid = tx.content.get("uuid") if hasattr(tx, "content") else None
            if new_uuid:
                for existing in account.transactions:
                    if existing.content.get("uuid") == new_uuid:
                        return True
                return False

            for existing in account.transactions:
                if (
                    str(existing.getDate()) == str(tx.getDate())
                    and existing.type == tx.type
                    and existing.getValue() == tx.getValue()
                ):
                    return True
            return False

        if acct_from and tx_from:
            acct_from.resolve_reference()
            tx_from.resolve_reference()
            if not _already_exists(tx_from, acct_from):
                acct_from.transactions.append(tx_from)

        if acct_to and tx_to:
            acct_to.resolve_reference()
            tx_to.resolve_reference()
            if not _already_exists(tx_to, acct_to):
                acct_to.transactions.append(tx_to)

    @staticmethod
    def parse(content: Any) -> CrossEntry | None:  # type: ignore[override]
        from .classAccount import Account
        from .classDepot import Depot
        from .classTransaction import Transaction

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

        crossEntry = CrossEntry(content)
        CrossEntry.crossEntryQueue.append(crossEntry)
        return crossEntry

    def __init__(self, content: Any) -> None:
        self.content = content
