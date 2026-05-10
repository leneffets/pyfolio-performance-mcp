from .helpers import *
from .classPortfolioPerformanceObject import PortfolioPerformanceObject
from .classDateObject import DateObject

from .classSecurity import Security

from .classTransaction import Transaction
from .classDepot import Depot
from .classCrossEntry import CrossEntry
from .classPortfolio import Portfolio

from .classFilters import Filters


def reset():
    """Reset all class-level state. Call before loading a new portfolio."""
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