# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from typing import Any

from .helpers import combine_paths
from .portfolio_performance_object import PortfolioPerformanceObject


class Account(PortfolioPerformanceObject):
    """
    The class that manages a money account and its transactions.
    """

    def __init__(self, content: dict[str, Any], reference: str | None = None) -> None:
        self.transactions: list[Any] = []
        self.uuid: str | None = content.get("uuid")
        self.name: str | None = content.get("name")
        self.content = content
        self.balance: int | None = None
        self.reference = reference
        Portfolio.currentPortfolio.register_path(content["referencePath"], self)  # type: ignore[attr-defined]

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
        result = 0
        for t in self.transactions:
            result += t.get_value()
        self.balance = result
        return result

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

        if "@reference" in content:
            return Account(content, content["@reference"])

        rslt = Account(content)
        rslt._parse_transactions(content)
        Portfolio.currentPortfolio.register_uuid(content["uuid"], rslt)  # type: ignore[attr-defined]

        return rslt

    def _parse_transactions(self, content: dict[str, Any]) -> None:
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

            transaction_obj = Transaction.parse(transact)
            if "uuid" in transact:
                Portfolio.currentPortfolio.register_uuid(  # type: ignore[attr-defined]
                    transact["uuid"], transaction_obj
                )
            self.transactions.append(transaction_obj)
            num += 1

    def resolve_reference(self) -> None:
        super().resolve_reference()

        for transaction in self.transactions:
            transaction.resolve_reference()

        self._resolve_referenced_transactions()

    def _resolve_referenced_transactions(self) -> None:
        """Resolve <account-transaction> @reference entries to actual objects.

        These appear when CSV-imported accounts share transactions across
        accounts via XStream references. Each reference path is rewritten
        to absolute, looked up via the Portfolio path map, and the
        resolved transaction is appended to this account's list (and the
        account is set on the transaction).
        """
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

            # Translate the relative reference into an absolute path.
            # The base must be the reference_path of the current account-transaction
            # node (not a hardcoded root), so that nested accounts (e.g. those
            # stored inside cross_entry/account_to) resolve correctly.
            # We use the same combine_paths() helper used everywhere else.
            #
            # The @reference on a transaction node is relative to that node itself,
            # so the base is: <account.reference_path>/transactions/account-transaction
            account_tx_base = (
                self.content["referencePath"] + "/transactions/account-transaction"
            )
            abs_path = combine_paths(account_tx_base, ref_path)

            try:
                resolved = Portfolio.currentPortfolio.get_object_by_path(  # type: ignore[attr-defined]
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

            if not hasattr(resolved, "set_account"):
                continue

            resolved.set_account(self)
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

from .portfolio import Portfolio  # noqa: E402
from .transaction import Transaction  # noqa: E402
