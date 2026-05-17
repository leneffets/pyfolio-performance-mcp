import re
from typing import Any

from .helpers import combine_paths, copy_from

_array_regex = re.compile(r"\[(\d+)\]$")


class PortfolioPerformanceObject:
    """
    Base class for most objects in the library.
    Offers basic functionality needed, such as:
    - cache of already parsed objects,
    - resolution of objects that are defined by references,
    - general parsing methods.
    """

    parsed: dict[str, "PortfolioPerformanceObject"] = {}
    reference_skip: int = 3

    _attribute_list: list[str] = []
    _attributes: dict[str, Any] = {}
    _attrib_object_map: dict[str, dict[str, "PortfolioPerformanceObject"]] = {}
    reference: str | None = None
    content: dict[str, Any] = {}

    def _get_attribute(self, name: str) -> Any:
        """
        :param name: the name of the attribute
        :type name: str

        :return: the stored value
        :type: arbitrary
        """
        if name in self._attributes:
            return self._attributes[name]
        return None

    def _set_attribute(self, name: str, value: Any) -> None:
        """
        :param name: name of the attribute
        :type name: str

        :param value: value to store
        :type value: arbitrary
        """
        self._attributes[name] = value

        # Connect attribute to the corresponding class map
        if name not in self.__class__._attrib_object_map:
            self.__class__._attrib_object_map[name] = {}
        self.__class__._attrib_object_map[name][value] = self

    @classmethod
    def get_object_by_attribute(cls, attr: str, value: str) -> "PortfolioPerformanceObject | None":
        """
        Note it only works if there is a single object for the attribute
        and the value. For example, we can ask for the attribute `isin`
        of a security with the value `DE0005190003` leading to BMW.

        :param attr: the attribute we are looknig for
        :type attr: str

        :param value: the value the attribute should have
        :type value: str

        :return: the store object for the value
        :type: object
        """
        if attr not in cls._attrib_object_map:
            return None
        attr_map = cls._attrib_object_map[attr]
        if value not in attr_map:
            return None
        return attr_map[value]

    @classmethod
    def parse_by_reference(
        cls, parent_node: Any, reference: str
    ) -> "PortfolioPerformanceObject | None":
        return None

    @classmethod
    def parse_content(cls, data: dict[str, Any]) -> "PortfolioPerformanceObject | None":
        return None

    @classmethod
    def parse(cls, parent_node: Any, data: dict[str, Any]) -> "PortfolioPerformanceObject | None":
        """
        This methods parses portfolio performance objects.
        It returns the parsed result of the referenced xml.

        :param root: Root of the parsing, in case it is needed to resolve references.
        :type root: Portfolio

        :param data: Object to be parsed.
        :type data: dict object

        :return: Parsed object.
        :type: Subclass of PortfolioPerformanceObject
        """
        rslt: PortfolioPerformanceObject | None = None
        if "@reference" in data:
            rslt = cls.parse_by_reference(parent_node, data["@reference"])
        else:
            rslt = cls.parse_content(data)
            # rslt.parseAttributes()

        return rslt

    def copy_from(self, other: Any) -> None:
        copy_from(self, other)

    def resolve_reference(self) -> None:
        from .portfolio import Portfolio  # lazy to avoid circular import

        if self.reference is None:
            return
        combined = combine_paths(self.content["referencePath"], self.reference)

        other = Portfolio.currentPortfolio.get_object_by_path(combined)  # type: ignore[attr-defined]
        if other is None:
            raise RuntimeError(
                f"Cannot resolve reference [{self.__class__}]: "
                + str(combined)
                + " from "
                + str(self.reference)
            )

        self.copy_from(other)
