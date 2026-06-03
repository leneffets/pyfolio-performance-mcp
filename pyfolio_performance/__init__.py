# ruff: noqa: I001 — import order must respect circular dependency chain

from .helpers import MyCustomClassEncoder, combine_paths, copy_from
from .date_object import DateObject
from .portfolio_performance_object import PortfolioPerformanceObject
from .portfolio import Portfolio
from .cross_entry import CrossEntry
from .depot import Depot
from .filters import Filters
from .security import Security
from .transaction import Transaction

__all__ = [
    "CrossEntry",
    "DateObject",
    "Depot",
    "Filters",
    "Portfolio",
    "PortfolioPerformanceObject",
    "Security",
    "Transaction",
    "MyCustomClassEncoder",
    "combine_paths",
    "copy_from",
]


def reset() -> None:
    """Reset all class-level state.

    No longer required before each Portfolio() — Portfolio.__init__ now
    invokes this automatically. Kept for backwards compatibility and for
    callers that want to clear state without loading a new portfolio.
    """
    Portfolio._reset_class_state()  # type: ignore[reportPrivateUsage]
