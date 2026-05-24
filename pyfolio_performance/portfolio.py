from typing import Any

import xmltodict

from .security import Security


class Portfolio:
    """
    The main class to parse and access different aspects of a portfolio stored in a XML file.

    Uses the XML file created by portfolio performance.

    :param filename: The path of the XML file to parse.
    :type filename: str
    """

    TRANSACTION_ALL = "all"
    TRANSACTION_DEPOT = "depot"
    TRANSACTION_ACCOUNT = "account"

    parent_map: dict[str, Any] = {}
    uuid_map: dict[str, Any] = {}
    path_map: dict[str, Any] = {}

    @staticmethod
    def _reset_class_state() -> None:
        """Clear all class-level caches.

        Called automatically by Portfolio.__init__ so that loading a second
        portfolio in the same process does not leak state from the previous
        one. Also exposed via the top-level reset() helper for explicit use.
        """
        Security.security_name_map.clear()
        Security.security_isin_map.clear()
        Security.security_wkn_map.clear()
        Security.security_nums.clear()
        Security.most_recent_value = None
        Transaction.reference_map.clear()
        Depot.depot_map.clear()
        CrossEntry.cross_entry_queue.clear()
        Portfolio.uuid_map.clear()
        Portfolio.path_map.clear()
        Portfolio.parent_map.clear()

    def __init__(self, filename: str) -> None:
        # Auto-reset class-level caches so loading a second portfolio in
        # the same process is safe without needing an explicit reset() call.
        Portfolio._reset_class_state()

        Portfolio.currentPortfolio = self  # type: ignore[attr-defined]
        with open(filename) as f:
            xml_content = f.read()
        self.content = xmltodict.parse(xml_content)

        self._parse_securities()  # needs to be done first
        self._parse_accounts()
        self._parse_depots()
        CrossEntry.process_cross_entries()

        for dep in self.depotList:
            dep.resolve_reference()
            dep.clear_duplicate_transactions()
        for acc in self.accList:
            acc.resolve_reference()

    def _parse_securities(self) -> None:
        self.securityList = []

        client = self.content.get("client") or {}
        securities_section = client.get("securities") or {}
        securities = securities_section.get("security")
        if securities is None:
            return

        if isinstance(securities, dict):
            securities = [securities]

        for num, sec in enumerate(securities):
            sec["num"] = num
            sec_obj = Security.parse_content(sec)
            if "uuid" in sec:
                self.uuid_map[sec["uuid"]] = sec_obj
            self.securityList.append(sec_obj)

    def _parse_accounts(self) -> None:
        self.accList = []

        num = 1
        ref_path = "client/accounts/account"

        client = self.content.get("client") or {}
        accounts_section = client.get("accounts") or {}
        accounts = accounts_section.get("account")
        if accounts is None:
            return

        if isinstance(accounts, dict):
            accounts = [accounts]

        for acc in accounts:
            acc["referencePath"] = ref_path
            if num > 1:
                acc["referencePath"] += f"[{num}]"
            current_account = Account.parse(acc)
            self.accList.append(current_account)
            num += 1

        for acc in self.accList:
            acc.resolve_reference()

    def _parse_depots(self) -> None:
        self.depotList = []

        num = 1
        ref_path = "client/portfolios/portfolio"

        client = self.content.get("client") or {}
        portfolios_section = client.get("portfolios") or {}
        depots = portfolios_section.get("portfolio")
        if depots is None:
            return

        if isinstance(depots, dict):
            depots = [depots]

        for dep in depots:
            dep["referencePath"] = ref_path
            if num > 1:
                dep["referencePath"] += f"[{num}]"
            current_depot = Depot.parse(dep)
            self.depotList.append(current_depot)
            num += 1

        for dep in self.depotList:
            dep.resolve_reference()

    def register_uuid(self, uuid: str, obj: Any) -> None:
        if uuid is not None:
            self.uuid_map[uuid] = obj

    def register_path(self, path: str, obj: Any) -> None:
        if path is not None:
            self.path_map[path] = obj

    def get_object_by_path(self, path: str) -> Any:
        if path in self.path_map:
            return self.path_map[path]
        return None

    def get_depots(self) -> list[Any]:
        """
        Returns the list of Depot objects in the portfolio.

        :return: The extracted Depot list.
        :type: list(Depot)
        """
        return self.depotList

    def get_accounts(self) -> list[Any]:
        """
        Returns the list of Account objects in the portfolio.

        :return: The extracted Account list.
        :type: list(Account)
        """
        return self.accList

    def get_securities(self) -> list[Any]:
        """
        Returns the list of all unique securities in any depot.
        :return: The list.
        :type: list(Security)
        """
        return self.securityList

    def get_shares(self, the_security: Any) -> int | float:
        """
        Returns the number of shares that the given security objects has
        in the portfolio overall.

        :param the_security: The security queried.
        :type the_security: Security

        :return: The number of shares in all depots summed up.
        :type: float
        """
        if the_security is None:
            return 0

        val = 0
        for dep in self.get_depots():
            sec_values = dep.get_securities()
            if the_security in sec_values:
                val += sec_values[the_security]
        return val

    def get_total_transactions(self, transaction_type: str) -> list[Any]:
        """
        Returns the list of transactions across depots and/or accounts.

        For TRANSACTION_ALL the result is deduplicated for buy/sell pairs:
        a buy/sell event in Portfolio Performance is recorded twice — once
        on the account (cash flow) and once on the depot (share movement).
        Both entries carry the same value, so naive summing across ALL
        would double-count. We keep the account-side and drop the
        depot-side, since the cash-flow representation is the canonical
        one for value aggregation. Per-depot share calculations rely on
        Depot.transactions directly and are unaffected.

        :return: The extracted transaction list.
        :type: list(Transaction)
        """
        total_transactions = []
        if (
            transaction_type == Portfolio.TRANSACTION_DEPOT
            or transaction_type == Portfolio.TRANSACTION_ALL
        ):
            for depot in self.get_depots():
                for t in depot.get_transactions():
                    if transaction_type == Portfolio.TRANSACTION_ALL and t.type in ("BUY", "SELL"):
                        continue
                    total_transactions.append(t)
        if (
            transaction_type == Portfolio.TRANSACTION_ACCOUNT
            or transaction_type == Portfolio.TRANSACTION_ALL
        ):
            for acc in self.get_accounts():
                total_transactions.extend(acc.get_transactions())
        return total_transactions

    def get_investment_into(self, security: Any, before: Any = None) -> int:
        """
        Computes how much is invested into a specific security before a
        given date. If no date is given, the total investment is calculated.

        :return: value in cents of investment
        :type: int
        """
        clusters: dict[str, int] = {"value": 0}
        my_filter = Filters.f_security_transaction(security)
        if before is not None:
            my_filter = Filters.f_and(my_filter, Filters.fDate(before, None))  # type: ignore[attr-defined]

        def fn_cluster(x: Any, y: Any) -> str:
            return "value"

        def fn_aggregate(x: Any, y: Any) -> Any:
            return x + y.get_value()

        self.evaluate_cluster(clusters, my_filter, fn_cluster, fn_aggregate)

        return clusters["value"]

    def evaluate_cluster(
        self,
        clusters: dict[str, Any],
        fn_filter: Any,
        fn_get_cluster_id: Any,
        fn_aggregation: Any,
        transaction_type: str = TRANSACTION_ALL,
    ) -> None:
        """
        Evaluates all transactions of the portfolio as follows.
        Every transaction that is successfully filtered by fn_filter, gets
        put in a cluster through fn_get_cluster_id. The objects in the cluster
        are aggregated through the fn_aggregation function.

        :parameter clusters: The overall clusters.
        :type clusters: dict(object) / {k->v}

        :parameter fn_filter: Filter function. An entry needs to pass
            the filter with True to be considered.
        :type fn_filter: function(transaction) -> bool

        :parameter fn_get_cluster_id: Given the cluster and the transaction,
            this method gives the key to the cluster the transaction
            belongs to.
        :type fn_get_cluster_id: function({k->v}, Transaction) -> k

        :parameter fn_aggregation: The aggregation function that combines
            cluster values. This updates the cluster itself at the position
            cluster-id for every considered transaction.
        :type fn_aggregation: function(v, Transaction) -> v

        :parameter transaction_type: The type of transaction to consider.
            Default is TRANSACTION_ALL. Options are TRANSACTION_DEPOT and
            TRANSACTION_ACCOUNT.

        :return: Nothing is returned.
        :type: None
        """
        for transact in self.get_total_transactions(transaction_type):
            if not fn_filter(transact):
                continue
            cluster_id = fn_get_cluster_id(clusters, transact)
            clusters[cluster_id] = fn_aggregation(clusters[cluster_id], transact)


from pyfolio_performance.filters import Filters  # noqa: E402

from .account import Account  # noqa: E402
from .cross_entry import CrossEntry  # noqa: E402
from .depot import Depot  # noqa: E402
from .transaction import Transaction  # noqa: E402
