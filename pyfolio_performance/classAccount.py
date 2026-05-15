from .classPortfolioPerformanceObject import PortfolioPerformanceObject

class Account(PortfolioPerformanceObject):
    """
    The class that manages a money account and its transactions.
    """

    def __init__(self, content, reference=None):
        self.transactions = []
        self.uuid = content['uuid'] if 'uuid' in content else None
        self.name = content['name'] if 'name' in content else None
        self.content = content
        self.balance = None
        self.reference = reference
        Portfolio.currentPortfolio.registerPath(content['referencePath'], self)

    def copy_from(self, other):
        other.resolveReference()

        self.uuid = other.uuid
        self.name = other.name
        self.reference = other.reference
        self.transactions = other.transactions
        self.content = other.content
        # invalidate cached balance — recomputed from transactions on demand
        self.balance = None

    def getBalance(self):
        """
        :return: Balance of the account in cents.
        :type: int
        """
        if self.balance != None:
            return self.balance
        self.balance = 0
        for t in self.transactions:
            self.balance += t.getValue()
        return self.balance

    def getName(self):
        """
        :return: Name of the account.
        :type: str
        """
        return self.name

    def getTransactions(self):
        """
        :return: list of transactions in the account.
        :type: list(Transaction)
        """
        return self.transactions

    @staticmethod
    def parse(content):
        if 'referencePath' not in content:
            content['referencePath'] = 'client/accounts/account'
            
        if "@reference" in content.keys():
            return Account(content, content['@reference'])
        
        rslt =  Account(content)
        rslt._parseTransactions(content)
        Portfolio.currentPortfolio.registerUuid(content['uuid'], rslt)
        
        return rslt
    
    def _parseTransactions(self, content):
        if content.get('transactions') is None:
            return

        txs = content['transactions'].get('account-transaction')
        if txs is None:
            return

        if isinstance(txs, dict):
            txs = [txs]

        num = 1
        for transact in txs:
            if "@reference" in transact:
                num += 1
                continue

            transact['account'] = self

            transact['referencePath'] = content['referencePath'] + '/transactions/account-transaction'
            if num > 1:
                transact['referencePath'] += '[%d]' % num
            transactionObject = Transaction.parse(transact)
            if 'uuid' in transact:
                Portfolio.currentPortfolio.registerUuid(transact['uuid'], transactionObject)
            self.transactions.append(transactionObject)
            num += 1
    
    def resolveReference(self):
        super().resolveReference()

        for transaction in self.transactions:
            transaction.resolveReference()

        
        self._resolveReferencedTransactions()

    def _resolveReferencedTransactions(self):
        """Resolve <account-transaction> @reference entries to actual objects.

        These appear when CSV-imported accounts share transactions across
        accounts via XStream references. Each reference path is rewritten
        to absolute, looked up via the Portfolio path map, and the
        resolved transaction is appended to this account's list (and the
        account is set on the transaction).
        """
        transactions_node = self.content.get('transactions')
        if transactions_node is None:
            return

        txs = transactions_node.get('account-transaction')
        if txs is None:
            return

        # xmltodict returns a dict (not a list) for a single child element.
        if isinstance(txs, dict):
            txs = [txs]

        for transact in txs:
            if not isinstance(transact, dict) or "@reference" not in transact:
                continue

            ref_path = transact.get('@reference', '')
            if not ref_path or not ref_path.startswith('../'):
                continue

            # Translate the relative reference into an absolute path
            # rooted at the canonical account-transaction location.
            parts = ref_path.split('/')
            abs_parts = ['client', 'accounts', 'account',
                         'transactions', 'account-transaction']
            for part in parts:
                if part == '..':
                    if len(abs_parts) > 1:
                        abs_parts.pop()
                else:
                    abs_parts.append(part)
            abs_path = '/'.join(abs_parts)

            try:
                resolved = Portfolio.currentPortfolio.getObjectByPath(abs_path)
            except Exception as e:
                # Path lookup itself failed — surface as repr, do not crash
                # the rest of the resolution loop.
                print("Reference lookup failed for %s: %r" % (abs_path, e))
                continue

            if resolved is None:
                # Reference points at something not (yet) registered —
                # silently skip; the second pass in Portfolio.__init__
                # will retry once depots are also parsed.
                continue

            if not hasattr(resolved, 'setAccount'):
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
        if self.name != None:
            return "Account/%s: %s" % (self.name, self.getBalance())
        return "Account/%s: %d" % (self.reference, self.getBalance())

from .classTransaction import *
from .classPortfolio import *