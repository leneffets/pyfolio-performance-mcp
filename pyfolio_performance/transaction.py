from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, ClassVar

from .cross_entry import CrossEntry
from .date_object import DateObject
from .portfolio_performance_object import PortfolioPerformanceObject
from .security import Security


class Transaction(PortfolioPerformanceObject):
    negative: ClassVar[list[str]] = [
        "TRANSFER_OUT",
        "REMOVAL",
        "INTEREST_CHARGE",
        "FEES",
        "TAXES",
        "BUY",
        "DELIVERY_OUTBOUND",
    ]
    positive: ClassVar[list[str]] = [
        "INTEREST",
        "DEPOSIT",
        "TRANSFER_IN",
        "DIVIDENDS",
        "SELL",
        "FEES_REFUND",
        "TAX_REFUND",
        "DELIVERY_INBOUND",
    ]

    negative_depot: ClassVar[list[str]] = ["DELIVERY_OUTBOUND", "SELL", "TRANSFER_OUT"]
    positive_depot: ClassVar[list[str]] = ["BUY", "DELIVERY_INBOUND", "TRANSFER_IN"]

    source_map: ClassVar[dict[str, Callable[[Transaction], str]]] = {
        "TRANSFER_IN": lambda x: "Transfer",
        "TRANSFER_OUT": lambda x: "Transfer",
        "DEPOSIT": lambda x: "Transfer",
        "REMOVAL": lambda x: "Type Removal",
        "INTEREST_CHARGE": lambda x: x.get_account_name(),
        "INTEREST": lambda x: x.get_account_name(),
        "TAXES": lambda x: (
            x.get_security().get_name() if x.get_security() is not None else "Tax"  # type: ignore[union-attr]
        ),
        "FEES": lambda x: (
            x.get_security().get_name()  # type: ignore[union-attr]
            if x.get_security() is not None
            else x.get_account_name()
        ),
        "FEES_REFUND": lambda x: (
            x.get_security().get_name()  # type: ignore[union-attr]
            if x.get_security() is not None
            else x.get_account_name()
        ),
        "DIVIDENDS": lambda x: x.get_security().get_name(),  # type: ignore[union-attr]
        "SELL": lambda x: "Trading",
        "BUY": lambda x: "Trading",
    }

    reference_map: ClassVar[dict[str, Transaction]] = {}

    def __init__(self, content: dict[str, Any], reference: str | None = None) -> None:
        from .portfolio import Portfolio  # lazy to avoid circular import

        self.reference = reference
        self.security: Security | None = None
        self.content = content

        Transaction.reference_map[content["referencePath"]] = self
        Portfolio.currentPortfolio.register_path(  # type: ignore[attr-defined]
            content["referencePath"],
            self,
        )

        if reference is not None:
            return

        self._account = content.get("account")
        self.type = content["type"]
        self.date = DateObject(content["date"])

    def copy_from(self, other: Transaction) -> None:
        self.reference = other.reference
        self._account = other._account
        self.type = other.type
        self.date = other.date
        self.content = other.content

    def to_dict(self) -> dict[str, Any]:
        return {"content": self.content, "reference": self.reference}

    def __repr__(self) -> str:
        try:
            return f"Transaction({self.type}, {self.date})"
        except Exception:
            return "Transaction without type or date"

    def set_account(self, account: Any) -> None:
        """
        Setter method for the account name.

        :param name: Name of the account.
        :type name: str
        """
        self._account = account

    def get_account_name(self) -> str:
        """
        Getter method for the account name.

        :return: Name of the account.
        :type: str
        """
        return self._account.name  # type: ignore[no-any-return, union-attr]

    scale = 100

    def get_value(self) -> int | float:
        try:
            val: int | float = int(self.content["amount"])
            if self.type in Transaction.negative:
                val = -val
            elif self.type not in Transaction.positive:
                val = self.get_security_based_value()
            return val
        except (KeyError, AttributeError, TypeError, ValueError):
            return 0

    def get_security_based_value(self) -> float:
        """
        Fallback value calculation for transactions without an `amount`:
        shares × current price, scaled back to cents.

        get_shares() returns the raw 10^8-scaled value from the XML and
        get_most_recent_value() returns a cent value, so divide by the
        share scale to land in cents.
        """
        sec = self.get_security()
        if sec is None:
            return 0
        return self.get_shares() * sec.get_most_recent_value() / 100000000

    def get_amount(self) -> int:
        try:
            return int(self.content["amount"])
        except (KeyError, TypeError, ValueError):
            return 0

    def get_shares(self) -> int:
        try:
            return int(self.content["shares"])
        except (KeyError, TypeError, ValueError):
            return 0

    def get_year(self) -> int:
        """
        Getter method for the year of the underlying date object.

        :return: year of the transaction.
        :type: int
        """
        return self.date.get_year()

    def get_month(self) -> int:
        """
        Getter method for the month of the underlying date object.

        :return: month of the transaction.
        :type: int
        """
        return self.date.get_month()

    def get_day(self) -> int:
        """
        Getter method for the day of the underlying date object.

        :return: day of the transaction.
        :type: int
        """
        return self.date.get_day()

    def get_date(self) -> DateObject:
        """
        Return the date object.

        :return: The included date object.
        :type: DateObject
        """
        return self.date

    def get_source_name(self) -> str:
        if self.type in Transaction.source_map:
            return Transaction.source_map[self.type](self)
        return self.get_security().get_name()  # type: ignore[union-attr]

    def get_security(self) -> Security | None:
        self.compute_security()
        return self.security

    def has_security(self) -> bool:
        return self.compute_security()

    security_pattern = re.compile(r"(\.\./)*securities/security\[(\d+)\]$")

    def compute_security(self) -> bool:
        if self.security is not None:
            return True

        sec_node = self.content.get("security") if isinstance(self.content, dict) else None
        if not isinstance(sec_node, dict):
            return False

        security = sec_node.get("@reference")
        if security is None:
            return False

        match = Transaction.security_pattern.search(security)
        if match:
            self.security = Security.get_security_by_num(int(match.group(2)))
            return True
        elif security.endswith("securities/security"):
            self.security = Security.get_security_by_num(1)
            return True

        raise RuntimeError(f"Security could not be resolved for transaction pattern '{security}'")

    def get_security_change(self) -> tuple[Security, int]:
        if not self.compute_security():
            raise RuntimeError("Security could not be resolved for transaction")

        assert self.security is not None
        val = int(self.content["shares"])
        if self.type in Transaction.negative_depot:
            val = -val
        return (self.security, val)

    #   {
    #     "uuid": "6ff55ee0-f3c7-410c-812b-424ad293ce97",
    #     "date": "2018-01-01T00:00",
    #     "currencyCode": "EUR",
    #     "amount": "899430",
    #     "shares": "0",
    #     "updatedAt": "2021-04-19T13:12:20.101395100Z",
    #     "type": "DEPOSIT"
    #   },

    @staticmethod
    def parse(content: dict[str, Any]) -> Transaction:  # type: ignore[override]
        if "@reference" in content:
            return Transaction(content, content["@reference"])

        transaction = Transaction(content, None)

        # Potential tasks
        ## Resolve "security" reference if field "security" exists
        transaction.compute_security()

        ## Continue if there is a "crossEntry" in there
        if "crossEntry" in content:
            content["crossEntry"]["referencePath"] = content["referencePath"] + "/crossEntry"
            CrossEntry.parse(content["crossEntry"])

        return transaction
