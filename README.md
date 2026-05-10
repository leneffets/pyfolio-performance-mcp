# pyfolio-performance

A python library to read Portfolio Performance XML files.

## Installation

```bash
pip install pyfolio-performance
```

## Local Development

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Test
python -c "
from pyfolio_performance import Portfolio, reset

reset()
portPerf = Portfolio('your_file.xml')

total_in = sum(a.getBalance() for a in portPerf.getAccounts())
depot_value = sum(sec.getMostRecentValue() * shares 
                   for d in portPerf.getDepots() 
                   for sec, shares in d.getSecurities().items())

print(f'Pay-in: {total_in/100:.2f} EUR')
print(f'Depot: {depot_value/100:.2f} EUR')
print(f'P/L: {(depot_value-total_in)/100:.2f} EUR')
"
```

## Quick Start

```python
from pyfolio_performance import Portfolio, reset

reset()  # clear any previous state
portPerf = Portfolio('your_file.xml')

# Get accounts and depots
for account in portPerf.getAccounts():
    print(f"{account.getName()}: {account.getBalance()/100} EUR")

for depot in portPerf.getDepots():
    for sec, shares in depot.getSecurities().items():
        print(f"{sec.getName()}: {shares} shares @ {sec.getMostRecentValue()/100} EUR")
```

## Test Files

- **Official test file:** https://github.com/portfolio-performance/portfolio/blob/master/name.abuchen.portfolio.ui/src/name/abuchen/portfolio/ui/parts/kommer.xml

## Docs

https://pyfolio-performance.readthedocs.io/en/latest/