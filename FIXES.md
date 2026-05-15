# Fixes Applied

## Round 2 — Library audit (May 2026)

Verified before/after against `kommer.xml` and a real `depot.xml`. Account
balances and per-depot share counts stayed identical; only the buggy
aggregations changed.

### R2.1 — BUY/SELL double-counting in `Portfolio.getTotalTransactions(ALL)`

PP records every buy/sell as two linked `Transaction` objects: one on the
account (cash flow) and one on the depot (share movement). Both carry the
same `amount`. Iterating with `TRANSACTION_ALL` returned both, so any
caller summing `getValue()` over BUY/SELL got double the real value.

**Impact reproduced on depot.xml:**
- `BUY` total before: -415,700.98 EUR
- `BUY` total after:  -207,850.49 EUR (matches account-only sum)
- Same factor-2 issue for `SELL`.
- `total_payin_eur` was unaffected (filters to DEPOSIT/REMOVAL/TRANSFER,
  which either appear only on the account side or self-cancel as +/-).

**Fix** (`classPortfolio.py`): in `getTotalTransactions(TRANSACTION_ALL)`,
skip the depot-side of BUY/SELL. The cash side is the canonical record;
share-count math goes through `Depot.getSecurities()` which reads the
depot transactions directly and is unaffected.

### R2.2 — `Transaction.getSecurityBasedValue()` unit mismatch + DELIVERY types

`getShares()` returns the raw 10^8-scaled value; `getMostRecentValue()`
returns cents. The product was ~10^8 too big.

This was reached for any type not listed in `Transaction.positive` /
`Transaction.negative` — most importantly `DELIVERY_INBOUND` and
`DELIVERY_OUTBOUND`, which exist in real exports (e.g. spinoffs).
On depot.xml a single `DELIVERY_INBOUND` aggregated to ~26 trillion EUR.

**Fix** (`classTransaction.py`):
- `DELIVERY_INBOUND` → `positive`, `DELIVERY_OUTBOUND` → `negative`, so
  `getValue()` uses the `amount` field directly (PP fills it for delivery
  transactions, e.g. tax basis).
- `getSecurityBasedValue()` now divides by 10^8 (and returns 0 if no
  security is attached) so the fallback path is also correct.

After fix, `DELIVERY_INBOUND` on depot.xml: 3,103.99 EUR (sane).

### R2.3 — `Depot._parseTransactions` crash on single-transaction depot

Same pattern Fix #2 already applied to `Account`, but missed in `Depot`.
xmltodict returns a dict (not a list) when there is only one child, so
iterating `content['transactions']['portfolio-transaction']` would walk
the dict's keys and crash. Also added an `@reference` skip analogous to
the Account fix.

**Fix** (`classDepot.py`): wrap dict→list, skip reference-only entries,
preserve the index counter for path generation.

### R2.4 — `DateObject.__repr__` missing zero-padding

`"%d-%d-%d"` produced `"2020-1-7"` instead of `"2020-01-07"`. Strings were
not ISO 8601 and sorted incorrectly lexicographically.

**Fix** (`classDateObject.py`): `"%04d-%02d-%02d"`.

### R2.5 — `Account.copy_from` missing `content` and `balance`

Inconsistent with `Depot.copy_from`. An Account resolved via `@reference`
kept the stub `{'@reference': '...'}` as its `content`, and a previously
cached `balance` was not invalidated.

**Fix** (`classAccount.py`): also call `other.resolveReference()` first,
copy `content`, reset `balance = None` so it is recomputed from the
fresh transaction list.

### R2.6 — `Security.getLogo` overwriting on every iteration

The loop over the attribute string list assigned `self.logo = string` on
every non-"logo" entry, so the last one always won. Looks like a
forgotten `break`.

**Fix** (`classSecurity.py`): `break` after the first non-marker string.

### R2.7 — Cleanup

- `Security.getSecurityByNum` now has the `@staticmethod` decorator it
  was missing (worked by accident, no behavioural change).
- New `Portfolio._resetClassState()` is invoked automatically at the
  start of every `Portfolio.__init__`, so loading a second portfolio in
  the same process no longer requires a manual `reset()` call. The
  top-level `reset()` helper still exists and now delegates to it.

---

## Round 1

## 10 Bug Fixes

### 11. classCrossEntry.py - Missing account-transfer handler
**Line ~16-17** - Account-transfer crossEntries were completely skipped, causing
cross-account transfers to only record one side.

The `processCrossEntries()` method had:
```python
else:
    pass  # still open to handle class="account-transfer"
```

This meant mirror transactions (e.g., `transactionTo` or `transactionFrom` inside
the crossEntry) were parsed as Transaction objects but never added to the
counterparty account's transaction list.

**Impact**: Trade Republic account balance read €48,784.04 instead of €33,982.97
— off by 4 missing TRANSFER transactions (3 TRANSFER_IN, 1 TRANSFER_OUT).

**Fix**: Replaced the `pass` with a call to `CrossEntry.crossEntry_accountTransfer()`
that resolves the counterparty account and appends the mirror transaction.
Dedup by `(date, type, amount)` prevents double-adding.

```python
@staticmethod
def crossEntry_accountTransfer(nextEntry):
    acct_from = nextEntry.content.get("accountFrom")
    acct_to = nextEntry.content.get("accountTo")
    tx_from = nextEntry.content.get("transactionFrom")
    tx_to = nextEntry.content.get("transactionTo")

    def _already_exists(tx, account):
        for existing in account.transactions:
            if (str(existing.getDate()) == str(tx.getDate())
                    and existing.type == tx.type
                    and existing.getValue() == tx.getValue()):
                return True
        return False

    if acct_from and tx_from:
        acct_from.resolveReference()
        tx_from.resolveReference()
        if not _already_exists(tx_from, acct_from):
            acct_from.transactions.append(tx_from)

    if acct_to and tx_to:
        acct_to.resolveReference()
        tx_to.resolveReference()
        if not _already_exists(tx_to, acct_to):
            acct_to.transactions.append(tx_to)
```

### 10. classAccount.py - CSV reference resolution
**Line ~100-127** - Fixed path construction for resolving @reference attributes in CSV imports.

```python
def _resolveReferencedTransactions(self):
    base_path = 'client/accounts/account/transactions/account-transaction'
    # Fixed: explicitly build from ['client', 'accounts', 'account', 'transactions', 'account-transaction']
    # instead of broken path calculation
    abs_parts = ['client', 'accounts', 'account', 'transactions', 'account-transaction']
```

**Also**: classTransaction.py:7 - Added `TAX_REFUND` to `positive` list.

```python
positive = ['INTEREST', 'DEPOSIT', 'TRANSFER_IN', 'DIVIDENDS', 'SELL', 'FEES_REFUND', 'TAX_REFUND']
```

Without this, TAX_REFUND fell through to `getSecurityBasedValue()` which failed (no security), causing:
- 27 CSV-referenced transactions not being resolved
- Balance off by 7 cents (566.10 vs 566.17 EUR)
- Error messages in output

### 9. classPortfolio.py - Single item handling (dict vs list)
**Line ~39, 49, 70** - When only 1 security/account/depot exists, xmltodict returns dict not list.

```python
# Fix for securities
securities = self.content['client']['securities']['security']
if isinstance(securities, dict):
    securities = [securities]

# Fix for accounts
accounts = self.content['client']['accounts']['account']
if isinstance(accounts, dict):
    accounts = [accounts]

# Fix for depots
depots = self.content['client']['portfolios']['portfolio']
if isinstance(depots, dict):
    depots = [depots]
```

### 1. classDepot.py - Null check for transactions
**Line ~123** - Portfolio without transactions caused crash.

```python
def _parseTransactions(self, content):
    if content.get('transactions') is None:
        return
    # ... rest of method
```

### 2. classAccount.py - Skip reference entries + handle single transaction
**Line ~63** - Prevented duplicate transaction processing and handled single transaction (dict vs list).

```python
def _parseTransactions(self, content):
    if content.get('transactions') is None:
        return

    txs = content['transactions'].get('account-transaction')
    if txs is None:
        return

    if isinstance(txs, dict):
        txs = [txs]
    # ... rest of method
```

### 3. classTransaction.py - Keep values in cents
**Line ~82-87** - Values are stored in cents (1000000 = 10,000.00 EUR = 1000000 cents).

```python
def getValue(self):
    try:
        val = int(self.content["amount"])  # keep in cents
        if self.type in Transaction.negative:
            val = -val
        # ... rest of method
```

### 4. classSecurity.py - Price scale
**Line ~14** - XML stores prices with 8 decimal places (15398000000 = 153.98 EUR = 1539800 cents).

```python
pricescale = 1000000  # scale to cents
```

### 5. classSecurity.py - Handle single price (dict vs list)
**Line ~62** - When only 1 price exists, xmltodict returns dict not list.

```python
if isinstance(priceList, dict):
    priceList = [priceList]
```

### 6. classSecurity.py - Improved getLogo error handling
**Line ~31** - Added specific exception handling instead of bare except.

### 7. classPortfolio.py - File handle leak
**Line ~23** - Use context manager for file handle.

### 8. classTransaction.py - Safer getAmount/getShares
**Line ~100-106** - Added try/except for KeyError/ValueError.

## Test Files

- **Official test file:** https://github.com/portfolio-performance/portfolio/blob/master/name.abuchen.portfolio.ui/src/name/abuchen/portfolio/ui/parts/kommer.xml
  - Download: `curl -sL "https://raw.githubusercontent.com/portfolio-performance/portfolio/master/name.abuchen.portfolio.ui/src/name/abuchen/portfolio/ui/parts/kommer.xml" -o kommmer.xml`

## To Test

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "
from pyfolio_performance import Portfolio

# Test sample file
portPerf = Portfolio('kommer.xml')
total_in = sum(a.getBalance() for a in portPerf.getAccounts())
depot_value = sum(sec.getMostRecentValue() * shares 
                   for d in portPerf.getDepots() 
                   for sec, shares in d.getSecurities().items())
print(f'Pay-in={total_in:.2f}, Depot={depot_value:.2f}, P/L={depot_value-total_in:.2f}')
"
```

Expected output (values in EUR):
- Pay-in=11539.15, Depot=23230.31, P/L=11691.16