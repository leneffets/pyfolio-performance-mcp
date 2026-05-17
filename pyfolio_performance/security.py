from typing import Any

from .date_object import DateObject
from .portfolio_performance_object import PortfolioPerformanceObject


class Security(PortfolioPerformanceObject):
    """
    A class that manages securities.
    """

    reference_skip = 0
    security_name_map: dict[str, "Security"] = {}
    security_isin_map: dict[str, "Security"] = {}
    security_wkn_map: dict[str, "Security"] = {}
    security_nums: dict[int, "Security"] = {}
    most_recent_value: int | float | None = None
    pricescale = 1000000  # scale factor to reach euro value in cents

    def __init__(self, data: dict[str, Any]) -> None:
        self._attributeList = [
            "uuid",
            "name",
            "currencyCode",
            "isin",
            "tickerSymbol",
            "wkn",
            "feed",
        ]
        self.data = data
        self.name: str = data["name"]
        self.logo: str | None = None
        self.isin = data.get("isin")
        self.wkn = data.get("wkn")
        self.most_recent_value = None
        Security.security_nums[data["num"]] = self
        Security.security_name_map[self.name] = self
        if self.isin is not None:
            Security.security_isin_map[self.isin] = self
        if self.wkn is not None:
            Security.security_wkn_map[self.wkn] = self

    def get_logo(self) -> str | None:
        """
        :return: Logo of the security
        :type: str
        """
        if self.logo is not None:
            return self.logo

        try:
            attributes = self.data.get("attributes", {}).get("map", {}).get("entry")
            if attributes is None:
                return None

            string_list = attributes.get("string", [])
            if isinstance(string_list, list):
                for string in string_list:
                    if string == "logo":
                        continue
                    self.logo = string
                    break
            elif isinstance(string_list, str) and string_list != "logo":
                self.logo = string_list
        except (KeyError, TypeError):
            pass

        return self.logo

    @staticmethod
    def get_security_by_num(num: int) -> "Security":
        return Security.security_nums[num - 1]  # -1 because the num starts at 1

    def get_most_recent_value(self) -> int | float:
        """
        :return: Current security price from the file in Euro.
        :type: float
        """
        if self.most_recent_value is not None:
            return self.most_recent_value

        prices = self.data.get("prices")
        if prices is None:
            print(f"No price list found for {self}")
            return 0

        price_list = prices.get("price")
        if price_list is None:
            print(f"No price list found for {self}")
            return 0

        if isinstance(price_list, dict):
            price_list = [price_list]

        newest_date = DateObject("0000-00-00")
        newest_xml = None

        for price in price_list:
            if isinstance(price, str):  # skip the text elements
                continue
            price_date = DateObject(price["@t"])
            if price_date.get_order_value() < newest_date.get_order_value():
                continue
            newest_date = price_date
            newest_xml = price

        if newest_xml is None:
            self.most_recent_value = 0
        else:
            self.most_recent_value = int(newest_xml["@v"]) / self.pricescale
        return self.most_recent_value

    def get_name(self) -> str:
        """
        :return: Name of the security
        :type: str
        """
        return self.name

    @staticmethod
    def _get_security_by_map(map: dict[str, "Security"], key: str) -> "Security | None":
        if key in map:
            return map[key]
        return None

    @staticmethod
    def get_security_by_name(name: str) -> "Security | None":
        """
        :param: Name of security that should be returned.
        :type: str

        :return: existing security object or None
        :type: Security
        """
        return Security.security_name_map.get(name)

    @staticmethod
    def get_security_by_isin(isin: str) -> "Security | None":
        """
        :param: Isin of security that should be returned.
        :type: str

        :return: existing security object or None
        :type: Security
        """
        return Security.security_isin_map.get(isin)

    @staticmethod
    def get_security_by_wkn(wkn: str) -> "Security | None":
        """
        :param: Wkn of security that should be returned.
        :type: str

        :return: existing security object or None
        :type: Security
        """
        return Security.security_wkn_map.get(wkn)

    @staticmethod
    def parse_content(data: dict[str, Any]) -> "Security":
        return Security(data)

    def __repr__(self) -> str:
        return f"Security/{self.get_name()}"
