import xmltodict

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

    parent_map = {}
    uuid_map = {}
    path_map = {}

    @staticmethod
    def _resetClassState():
        """Clear all class-level caches.

        Called automatically by Portfolio.__init__ so that loading a second
        portfolio in the same process does not leak state from the previous
        one. Also exposed via the top-level reset() helper for explicit use.
        """
        Security.securityNameMap.clear()
        Security.securityIsinMap.clear()
        Security.securityWknMap.clear()
        Security.securityNums.clear()
        Security.mostRecentValue = None
        Transaction.referenceMap.clear()
        Depot.depotMap.clear()
        CrossEntry.crossEntryQueue.clear()
        Portfolio.uuid_map.clear()
        Portfolio.path_map.clear()
        Portfolio.parent_map.clear()

    def __init__(self, filename):
        # Auto-reset class-level caches so loading a second portfolio in
        # the same process is safe without needing an explicit reset() call.
        Portfolio._resetClassState()

        Portfolio.currentPortfolio = self
        with open(filename, 'r') as f:
            xml_content = f.read()
        self.content = xmltodict.parse(xml_content)

        self._parseSecurities() # needs to be done first, other parsing could depend on it being done 
        self._parseAccounts()
        self._parseDepots()
        CrossEntry.processCrossEntries()
        
        # Ensuring every reference is resolved
        for dep in self.depotList:
            dep.resolveReference()
            dep.clearDuplicateTransactions()
        for acc in self.accList:
            acc.resolveReference()

    def _parseSecurities(self):
        self.securityList = []
        num = 0
        securities = self.content['client']['securities']['security']

        if isinstance(securities, dict):
            securities = [securities]

        for sec in securities:
            sec['num'] = num
            secObj = Security.parseContent(sec)
            self.uuid_map[sec['uuid']] = secObj
            self.securityList.append(secObj)
            num += 1

    def _parseAccounts(self):
        self.accList = []

        num = 1
        refPath = 'client/accounts/account'
        accounts = self.content['client']['accounts']['account']

        if isinstance(accounts, dict):
            accounts = [accounts]

        for acc in accounts:
            acc['referencePath'] = refPath
            if num > 1:
                acc['referencePath'] += "[%d]" % num
            currentAccount = Account.parse(acc)
            self.accList.append(currentAccount)
            num += 1

        for acc in self.accList:
            acc.resolveReference()

    def _parseDepots(self):
        self.depotList = []

        num = 1
        refPath = 'client/portfolios/portfolio'
        depots = self.content['client']['portfolios']['portfolio']

        if isinstance(depots, dict):
            depots = [depots]

        for dep in depots:
            dep['referencePath'] = refPath
            if num > 1:
                dep['referencePath'] += "[%d]" % num
            currentDepot = Depot.parse(dep)
            self.depotList.append(currentDepot)
            num += 1

        for dep in self.depotList:
            dep.resolveReference()

    def registerUuid(self, uuid, obj):
        if uuid != None:
            self.uuid_map[uuid] = obj

    def registerPath(self, path, obj):
        if path != None:
            self.path_map[path] = obj

    def getObjectByPath(self, path):
        if path in self.path_map:
            return self.path_map[path]
        return None

    def getDepots(self):
        """
        Returns the list of Depot objects in the portfolio.

        :return: The extracted Depot list.
        :type: list(Depot)
        """
        return self.depotList


    def getAccounts(self):
        """
        Returns the list of Account objects in the portfolio.

        :return: The extracted Account list.
        :type: list(Account)
        """
        return self.accList

    def getSecurities(self):
        """
        Returns the list of all unique securities in any depot.
        :return: The list.
        :type: list(Security)
        """
        return self.securityList

    def getShares(self, theSecurity):
        """
        Returns the number of shares that the given security objects has in the portfolio overall.

        :param theSecurity: The security queried.
        :type theSecurity: Security

        :return: The number of shares in all depots summed up.
        :type: float
        """
        if theSecurity == None:
            return 0  # if it is not in, we dont have it in the Portfolio

        val = 0
        for dep in self.getDepots():
            secVals = dep.getSecurities()
            if theSecurity in secVals:
                val += secVals[theSecurity]
        return val

    def getTotalTransactions(self, transactionType):
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
        totalTransactions = []
        if transactionType == Portfolio.TRANSACTION_DEPOT or transactionType == Portfolio.TRANSACTION_ALL:
            for depot in self.getDepots():
                for t in depot.getTransactions():
                    if (transactionType == Portfolio.TRANSACTION_ALL
                            and t.type in ('BUY', 'SELL')):
                        # depot-side of a buy/sell — skip, account-side
                        # carries the cash flow
                        continue
                    totalTransactions.append(t)
        if transactionType == Portfolio.TRANSACTION_ACCOUNT or transactionType == Portfolio.TRANSACTION_ALL:
            for acc in self.getAccounts():
                totalTransactions.extend(acc.getTransactions())
        return totalTransactions

    def getInvestmentInto(self, security, before=None):
        """
        Computes how much is invested into a specific security before a given date. If no date is given, the total investment is calculated.

        :return: value in cents of investment
        :type: int
        """

        clusters = {'value': 0}
        myFilter = Filters.fSecurityTransaction(security)
        if before != None:
            myFilter = Filters.fAnd(myFilter, Filters.fDate(before, None))

        def fn_cluster(x, y): return 'value'
        def fn_aggregate(x, y): return x+y.getValue()
        self.evaluateCluster(clusters, myFilter, fn_cluster, fn_aggregate)

        return clusters['value']

    def evaluateCluster(self, clusters, fn_filter, fn_getClusterId, fn_aggregation, transactionType=TRANSACTION_ALL):
        """
        Evaluates all transactions of the portfolio as follows.
        Every transaction that is successfully filtered by fn_filter, gets put in a cluster through fn_getClusterId.
        The objects in the cluster are aggregated through the fn_aggregation function.

        :parameter clusters: The overall clusters.
        :type clusters: dict(object) / {k->v}

        :parameter fn_filter: Filter function. An entry needs to pass the filter with True to be considered.
        :type fn_filter: function(transaction) -> bool

        :parameter fn_getClusterId: Given the cluster and the transaction, this method gives the key to the cluster the transaction belongs to.
        :type fn_getClusterId: function({k->v}, Transaction) -> k

        :parameter fn_aggregation: The aggregation function that combines cluster values. This updates the cluster itself at the position cluster-id for every considered transaction.
        :type fn_aggregation: function(v, Transaction) -> v
        
        :parameter transactionType: The type of transaction to consider. Default is TRANSACTION_ALL. Options are TRANSACTION_DEPOT and TRANSACTION_ACCOUNT.

        :return: Nothing is returned.
        :type: None
        """
        for transact in self.getTotalTransactions(transactionType):
            if not fn_filter(transact):
                continue
            clusterId = fn_getClusterId(clusters, transact)
            clusters[clusterId] = fn_aggregation(clusters[clusterId], transact)

from .classCrossEntry import *
from .classDepot import *
from .classAccount import *
from .helpers import *

from pyfolio_performance.classFilters import Filters