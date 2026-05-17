from typing import Any

from .classPortfolioPerformanceObject import PortfolioPerformanceObject

# ruff: noqa: N802, N999


class Account(PortfolioPerformanceObject):
    """
    The class that manages a money account and its transactions.
    """

    def __init__(self, content: dict[str, Any], reference: str | None = None) -> None:
        from .classPortfolio import Portfolio  # lazy to avoid circular import

        self.transactions: list[Any] = []
        self.uuid: str | None = content.get("uuid")
        self.name: str | None = content.get("name")
        self.content = content
        self.balance: int | None = None
        self.reference = reference
        Portfolio.currentPortfolio.registerPath(content["referencePath"], self)  # type: ignore[attr-defined]

    def copy_from(self, other: "Account") -> None:
        other.resolve_reference()

        self.uuid = other.uuid
        self.name = other.name
        self.reference = other.reference
        self.transactions = other.transactions
        self.content = other.content
        # invalidate cached balance — recomputed from transactions on demand
        self.balance = None

    def get_balance(self) -> int:
        """
        :return: Balance of the account in cents.
        :type: int
        """
        bal = self.balance
        if bal is not None:
            return bal
        self.balance = 0
        for t in self.transactions:
            self.balance += t.getValue()
        return self.balance

    def get_name(self) -> str:
        """
        :return: Name of the account.
        :type: str
        """
        return self.name  # type: ignore[return-value]

    def get_transactions(self) -> list[Any]:
        """
        :return: list of transactions in the account.
        :type: list(Transaction)
        """
        return self.transactions

    @staticmethod
    def parse(content: dict[str, Any]) -> "Account":  # type: ignore[override]
        if "referencePath" not in content:
            content["referencePath"] = "client/accounts/account"

        from .classPortfolio import Portfolio  # lazy to avoid circular import

        if "@reference" in content:
            return Account(content, content["@reference"])

        rslt = Account(content)
        rslt._parseTransactions(content)
        Portfolio.currentPortfolio.registerUuid(content["uuid"], rslt)  # type: ignore[attr-defined]

        return rslt

    def _parseTransactions(self, content: dict[str, Any]) -> None:
        if content.get("transactions") is None:
            return

        txs = content["transactions"].get("account-transaction")
        if txs is None:
            return

        if isinstance(txs, dict):
            txs = [txs]

        num = 1
        for transact in txs:
            if "@reference" in transact:
                num += 1
                continue

            transact["account"] = self

            transact["referencePath"] = (
                content["referencePath"] + "/transactions/account-transaction"
            )
            if num > 1:
                transact["referencePath"] += f"[{num}]"
            from .classPortfolio import Portfolio  # lazy to avoid circular import
            from .classTransaction import Transaction  # lazy to avoid circular import

            transaction_obj = Transaction.parse(transact)
            if "uuid" in transact:
                Portfolio.currentPortfolio.registerUuid(  # type: ignore[attr-defined]
                    transact["uuid"], transaction_obj
                )
            self.transactions.append(transaction_obj)
            num += 1

    def resolve_reference(self) -> None:
        super().resolve_reference()

        for transaction in self.transactions:
            transaction.resolve_reference()

        self._resolve_referencedTransactions()

    def _resolve_referencedTransactions(self) -> None:
        """Resolve <account-transaction> @reference entries to actual objects.

        These appear when CSV-imported accounts share transactions across
        accounts via XStream references. Each reference path is rewritten
        to absolute, looked up via the Portfolio path map, and the
        resolved transaction is appended to this account's list (and the
        account is set on the transaction).
        """
        from .classPortfolio import Portfolio  # lazy to avoid circular import

        transactions_node = self.content.get("transactions")
        if transactions_node is None:
            return

        txs = transactions_node.get("account-transaction")
        if txs is None:
            return

        # xmltodict returns a dict (not a list) for a single child element.
        if isinstance(txs, dict):
            txs = [txs]

        for transact in txs:
            if not isinstance(transact, dict) or "@reference" not in transact:
                continue

            ref_path = transact.get("@reference", "")
            if not ref_path or not ref_path.startswith("../"):
                continue

            # Translate the relative reference into an absolute path
            # rooted at the canonical account-transaction location.
            parts = ref_path.split("/")
            abs_parts = ["client", "accounts", "account", "transactions", "account-transaction"]
            for part in parts:
                if part == "..":
                    if len(abs_parts) > 1:
                        abs_parts.pop()
                else:
                    abs_parts.append(part)
            abs_path = "/".join(abs_parts)

            try:
                resolved = Portfolio.currentPortfolio.getObjectByPath(  # type: ignore[attr-defined]
                    abs_path
                )
            except Exception as e:
                # Path lookup itself failed — surface as repr, do not crash
                # the rest of the resolution loop.
                print(f"Reference lookup failed for {abs_path}: {e!r}")
                continue

            if resolved is None:
                # Reference points at something not (yet) registered —
                # silently skip; the second pass in Portfolio.__init__
                # will retry once depots are also parsed.
                continue

            if not hasattr(resolved, "setAccount"):
                continue

            resolved.setAccount(self)
            if resolved not in self.transactions:
                self.transactions.append(resolved)

    def __repr__(self) -> str:
        """
        Computes and returns the string representation of the object.
        Format 'Account/NAME: BALANCE'.

        :return: String representation of the account.
        :type: str
        """
        if self.name is not None:
            return f"Account/{self.name}: {self.get_balance()}"
        return f"Account/{self.reference}: {self.get_balance()}"
