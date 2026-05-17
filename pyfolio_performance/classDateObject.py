# ruff: noqa: N802, N803, N999

from __future__ import annotations


class DateObject:
    """
    Represents a data of a transaction.

    :param dateStr: Date string as used by portfolio performance in the XML.
    """

    def __init__(self, dateStr: str) -> None:
        self.date = dateStr

    def get_year(self) -> int:
        """
        :return: Returns the year of the date.
        :type: int
        """
        return int(self.date[:4])

    def get_month(self) -> int:
        """
        :return: Returns the month of the date.
        :type: int
        """
        return int(self.date[5:7])

    def get_day(self) -> int:
        """
        :return: Returns the day in the month of the date.
        :type: int
        """
        return int(self.date[8:10])

    def getOrderValue(self) -> int:
        """
        Used to order dates. Gives a comparable int s.t. `getOrderValue(a) <
        getOrderValue(b)` iff the date `a` was before the date `b`.
        :return: Returns an int representing the position in an order of the
                 date.
        :type: int
        """
        return self.get_day() + 31 * (self.get_month() - 1) + 31 * 12 * (self.get_year())

    def __repr__(self) -> str:
        """
        :return: ISO 8601 date string (YYYY-MM-DD), zero-padded.
        :type: str
        """
        return f"{self.get_year():04d}-{self.get_month():02d}-{self.get_day():02d}"
