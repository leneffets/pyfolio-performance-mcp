from datetime import datetime

from pyfolio_performance import Filters, Portfolio
from pyfolio_performance.transaction import Transaction

portfolio = Portfolio("portfolio.xml")
current_now = datetime.now()


def filter_month(entry: Transaction, month: int, year: int) -> bool:
    return year == entry.get_year() and month == entry.get_month()


filter_dividend = Filters.f_and(
    Filters.f_ensure_type_list(["DIVIDENDS"]),
    lambda entry: filter_month(entry, current_now.month, current_now.year),
)


# different clustering
def cluster_dividend(all_cluster: dict[str, int], entry: Transaction) -> str:
    return "val"


def aggregate_dividend(cluster: int | float, entry: Transaction) -> int | float:
    return cluster + entry.get_value()


divicluster: dict[str, int] = {"val": 0}
portfolio.evaluate_cluster(divicluster, filter_dividend, cluster_dividend, aggregate_dividend)
print(divicluster)


# Dividends are clustered by their name
def cluster_dividend2(all_cluster: dict[str, int], entry: Transaction) -> str:
    k = entry.get_source_name()
    if k not in all_cluster:
        all_cluster[k] = 0
    return k


divicluster2: dict[str, int] = {}
portfolio.evaluate_cluster(divicluster2, filter_dividend, cluster_dividend2, aggregate_dividend)
print(divicluster2)
