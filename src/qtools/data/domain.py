#!/usr/bin/env python3
"""
General Object class for the domain.
"""
import json
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import get_type_hints


@dataclass
class DomainObject:
    """Represents a database entry. Consists of the data fields, every db entry has."""
    name: str
    pid: str
    creatorId: str          # pylint: disable=invalid-name
    createDate: str         # pylint: disable=invalid-name
    lastChangerId: str      # pylint: disable=invalid-name
    lastChangeDate: str     # pylint: disable=invalid-name

    @classmethod
    def _create(cls, name: str, **kwargs) -> "DomainObject":
        """
        This factory function creates a DomainObject while ensuring, that the internal DB fields are all set to None.
        This function is usually not called directly, but by the factory function of a child class.

        Args:
            name (str): Name of the DomainObject

        Returns:
            [cls]: Created object
        """
        # Set default values for internal fields
        kwargs["name"] = name
        kwargs.setdefault("pid", None)
        kwargs.setdefault("creatorId", None)
        kwargs.setdefault("createDate", None)
        kwargs.setdefault("lastChangerId", None)
        kwargs.setdefault("lastChangeDate", None)
        return cls(**kwargs)

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def __post_init__(self) -> None:
        # Select all variables, that should be a dataclass, but are a dict and
        # turn them into the respective objects.
        # The field's type is evaluated using get_type_hints, because dataclasses are incompatible
        # with the string type hints, which are introduced with PEP 563 and "from __future__ import annotations"
        # This behavior may change in the future, if PEP 649 is implemented
        def gen():
            types = get_type_hints(type(self))
            for field in fields(self):
                name = field.name
                cls = types[name]
                if is_dataclass(cls) and isinstance(self.__dict__[name], Mapping):
                    yield name, cls

        objects = {name: cls(**self.__dict__[name]) for name, cls in gen()}
        self.__dict__.update(objects)

    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__

    def _handle_db_response(self, response) -> None:
        if not response["status"]:
            raise Exception(response["errorMessage"])
        # save pid
        self.pid = response["id"]
