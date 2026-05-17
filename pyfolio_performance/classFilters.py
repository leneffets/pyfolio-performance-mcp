# ruff: noqa: N802, N999

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .classDateObject import DateObject


class Filters:
    """
    Class that provides usefull filtering functions for the cluster analysis.
    """

    @staticmethod
    def fEnsureTypeList(typelist: list[str]) -> Callable[[Any], bool]:
        """
        :param typelist: List of types that are required by the filter.
        :type typelist: list(str)

        :return: A filter function that ensures the entry has a type
                 contained in the typelist.
        :type: Entry -> bool
        """
        return lambda x: x.type in typelist

    @staticmethod
    def fExcludeTypeList(typelist: list[str]) -> Callable[[Any], bool]:
        """
        :param typelist: List of types that are not allowed by the filter.
        :type typelist: list(str)

        :return: A filter function that ensures the entry has `not` a type
                 contained in the typelist.
        :type: Entry -> bool
        """
        return lambda x: x.type not in typelist

    @staticmethod
    def fDepotTransaction() -> Callable[[Any], bool]:
        """
        :return: A filter function that ensures the entry is a Depot
                 Transaction.
        :type: Entry -> bool
        """
        from .classTransaction import Transaction  # lazy to avoid circular import

        def _is_depot_tx(x: Any) -> bool:
            return isinstance(x, Transaction) and x.has_security()

        return _is_depot_tx

    @staticmethod
    def fSecurityTransaction(sec: Any) -> Callable[[Any], bool]:
        """
        :param sec: A security to filter for.
        :type sec: Security

        :return: A filter function that ensures the entry is a transaction
                 about the given security.
        :type: Entry -> bool
        """

        def _matches(x: Any) -> bool:
            try:
                return bool(x.get_security() == sec)
            except (RuntimeError, AttributeError, KeyError):
                return False

        return _matches

    @staticmethod
    def fBefore(date: DateObject) -> Callable[[Any], bool]:
        """
        :param year: The date to filter for.
        :type year: DateObject

        :return: A filter function that ensures the entry was made before or
                 on the date (<=).
        :type: Entry -> bool
        """

        def _before(x: Any) -> bool:
            return bool(
                x.get_year() < date.get_year()
                or (x.get_year() == date.get_year() and x.get_month() < date.get_month())
                or (
                    x.get_year() == date.get_year()
                    and x.get_month() == date.get_month()
                    and x.get_day() <= date.get_day()
                )
            )

        return _before

    @staticmethod
    def fYear(year: int) -> Callable[[Any], bool]:
        """
        :param year: The year to filter for.
        :type year: int

        :return: A filter function that ensures the entry was made in the
                 specified year.
        :type: Entry -> bool
        """
        return lambda x: x.get_year() == year

    @staticmethod
    def fMonth(month: int) -> Callable[[Any], bool]:
        """
        :param month: The month to filter for.
        :type month: int

        :return: A filter function that ensures the entry was made in the
                 specified month.
        :type: Entry -> bool
        """
        return lambda x: x.get_month() == month

    @staticmethod
    def fDay(day: int) -> Callable[[Any], bool]:
        """
        :param day: The day to filter for.
        :type day: int

        :return: A filter function that ensures the entry was made in the
                 specified day.
        :type: Entry -> bool
        """
        return lambda x: x.get_day() == day

    @staticmethod
    def fAnd(f1: Callable[[Any], bool], f2: Callable[[Any], bool]) -> Callable[[Any], bool]:
        """
        :param f1: First function.
        :type: function entry -> bool

        :param f2: Second function.
        :type: function entry -> bool

        :return: Returns a function that first evaluates both functions and
                 returns the `and`.
        :type: Entry -> bool
        """
        return lambda x: f1(x) and f2(x)

    @staticmethod
    def fOr(f1: Callable[[Any], bool], f2: Callable[[Any], bool]) -> Callable[[Any], bool]:
        """
        :param f1: First function.
        :type: function entry -> bool

        :param f2: Second function.
        :type: function entry -> bool

        :return: Returns a function that first evaluates both functions and
                 returns the `or`.
        :type: Entry -> bool
        """
        return lambda x: f1(x) or f2(x)
