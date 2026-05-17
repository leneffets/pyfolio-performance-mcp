# ruff: noqa: N802, N806

from __future__ import annotations

import json
from typing import Any


def combinePaths(absolute: str, relative: str) -> str:
    absoluteSplit = absolute.split("/")
    relativeSplit = relative.split("/")

    toRemove = 0
    for i in range(len(relativeSplit)):
        if relativeSplit[i] == "..":
            toRemove += 1
        else:
            break

    absoluteSplit = absoluteSplit[:-toRemove]
    relativeSplit = relativeSplit[toRemove:]
    return "/".join(absoluteSplit + relativeSplit)


def copy_from(self: Any, other: Any) -> None:
    if not isinstance(other, self.__class__):
        raise ValueError("Can only copy attributes from an instance of the same class")

    self.__dict__.update(other.__dict__)


class MyCustomClassEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        from .classAccount import Account
        from .classDepot import Depot
        from .classTransaction import Transaction

        if isinstance(obj, Transaction):
            return obj.to_dict()
        elif isinstance(obj, Account):
            return str(obj)
        elif isinstance(obj, Depot):
            return obj.content
        return super().default(obj)
