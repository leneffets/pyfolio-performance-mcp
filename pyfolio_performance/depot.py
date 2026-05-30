# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from typing import Any

from .portfolio_performance_object import PortfolioPerformanceObject


class Depot(PortfolioPerformanceObject):
    """
    The class that manages a depot and its transactions.
    """

    reference_skip = 6
    depot_map: dict[str, "Depot"] = {}
    current_depot = None
    scale = 100000000

    def __init__(self, content: dict[str, Any], reference: str | None = None) -> None:
        self.reference = reference

        self.transactions: list[Any] = []
        self.depotSecurities: dict[str, Any] | None = None
        self.content = content
        self.name = ""
        self.uuid = ""
        Portfolio.currentPortfolio.register_path(content["referencePath"], self)  # type: ignore[attr-defined]

        if reference is not None:
            return

        self.name = content["name"]
        self.uuid = content["uuid"]
        Depot.depot_map[self.name] = self
        Portfolio.currentPortfolio.register_uuid(content["uuid"], self)  # type: ignore[attr-defined]

    def copy_from(self, other: "Depot") -> None:
        other.resolve_reference()

        self.uuid = other.uuid
        self.name = other.name
        self.depotSecurities = other.depotSecurities
        self.content = other.content
        self.reference = other.reference
        self.transactions = other.transactions

    def resolve_reference(self) -> None:
        super().resolve_reference()

        for transaction in self.transactions:
            transaction.resolve_reference()

    def get_name(self) -> str:
        """
        :return: Name of the depot.
        :type: str
        """
        return self.name

    @staticmethod
    def get_depot_by_name(name: str) -> "Depot | None":
        """
        :param: Name of the depot that should be returned
        :type: str

        :return: Existing Depot or None
        :type: Depot | None
        """
        return Depot.depot_map.get(name)

    def get_securities(self) -> dict[str, Any]:
        """
        :return: Mapping of currently Securities to the number of contained shares
        :type: dict(Security -> float)
        """
        depot_sec = self.depotSecurities
        if depot_sec is not None:
            return depot_sec
        self.depotSecurities = {}

        for transaction in self.transactions:
            sec, change = transaction.get_security_change()
            if sec not in self.depotSecurities:
                self.depotSecurities[sec] = 0
            self.depotSecurities[sec] += change

        keys = list(self.depotSecurities)
        for k in keys:
            if self.depotSecurities[k] == 0:
                self.depotSecurities.pop(k)
            else:
                self.depotSecurities[k] = self.depotSecurities[k] / Depot.scale
                # Doing this scale at the end to get the most accurate result

        return self.depotSecurities

    def clear_duplicate_transactions(self) -> None:
        """
        This method is used to remove duplicate transactions from the depot.
        """
        # print("Clearing duplicates from %s" % self)
        # print(len(self.transactions))
        existing_reference = []
        new_transactions = []
        for transaction in self.transactions:
            if transaction.content["referencePath"] not in existing_reference:
                new_transactions.append(transaction)
                existing_reference.append(transaction.content["referencePath"])
        # print(len(new_transactions))
        self.transactions = new_transactions
        # print()

    @staticmethod
    def parse(content: dict[str, Any]) -> "Depot":  # type: ignore[override]
        if "@reference" in content:
            return Depot(content, content["@reference"])

        rslt = Depot(content)
        rslt._parse_transactions(content)

        if "referenceAccount" in content:
            content["referenceAccount"]["referencePath"] = (
                content["referencePath"] + "/referenceAccount"
            )
            Account.parse(content["referenceAccount"])

        return rslt

    def _parse_transactions(self, content: dict[str, Any]) -> None:
        if content.get("transactions") is None:
            return

        txs = content["transactions"].get("portfolio-transaction")
        if txs is None:
            return

        # xmltodict returns a dict (not a list) for a single child element.
        if isinstance(txs, dict):
            txs = [txs]

        num = 1
        for transact in txs:
            # Reference-only entries are resolved later via resolve_reference;
            # they do not need a fresh parse here, but the path index must
            # still be advanced so subsequent siblings get the correct path.
            if "@reference" in transact:
                num += 1
                continue

            transact["depot"] = self
            if "referencePath" not in content:
                content["referencePath"] = "../portfolio"
            if num == 1:
                transact["referencePath"] = (
                    content["referencePath"] + "/transactions/portfolio-transaction"
                )
            else:
                transact["referencePath"] = (
                    content["referencePath"] + f"/transactions/portfolio-transaction[{num}]"
                )
            transact["account"] = None

            transaction_obj = Transaction.parse(transact)
            if "uuid" in transact:
                Portfolio.currentPortfolio.register_uuid(  # type: ignore[attr-defined]
                    transact["uuid"], transaction_obj
                )
            self.transactions.append(transaction_obj)
            num += 1

    def get_transactions(self) -> list[Any]:
        """
        :return: list of transactions in the depot.
        :type: list(Transaction)
        """
        return self.transactions

    def __repr__(self) -> str:
        return f"Depot/{self.name}"

from .account import Account  # noqa: E402
from .portfolio import Portfolio  # noqa: E402
from .transaction import Transaction  # noqa: E402
