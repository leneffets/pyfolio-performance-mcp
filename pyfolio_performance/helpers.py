from __future__ import annotations

import json
from typing import Any


def combine_paths(absolute: str, relative: str) -> str:
    absolute_split = absolute.split("/")
    relative_split = relative.split("/")

    to_remove = 0
    for i in range(len(relative_split)):
        if relative_split[i] == "..":
            to_remove += 1
        else:
            break

    absolute_split = absolute_split[:-to_remove]
    relative_split = relative_split[to_remove:]
    return "/".join(absolute_split + relative_split)


def copy_from(self: Any, other: Any) -> None:
    if not isinstance(other, self.__class__):
        raise ValueError("Can only copy attributes from an instance of the same class")

    self.__dict__.update(other.__dict__)


class MyCustomClassEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        from .account import Account  # noqa: PLC0415
        from .depot import Depot  # noqa: PLC0415
        from .transaction import Transaction  # noqa: PLC0415

        if isinstance(o, Transaction):
            return o.to_dict()
        elif isinstance(o, Account):
            return str(o)
        elif isinstance(o, Depot):
            return o.content
        return super().default(o)
