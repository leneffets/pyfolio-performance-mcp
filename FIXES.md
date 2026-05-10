# Fixes Applied

## 8 Bug Fixes

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