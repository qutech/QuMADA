#!/usr/bin/env python3
"""
General Object class for the domain.
"""

from collections.abc import Mapping
import json
from dataclasses import dataclass, is_dataclass


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
    def _create(cls, name: str, **kwargs):
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

    def to_json(self):
        """
        Outputs json representation of the object as string.

        Returns:
            str: JSON representation
        """
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    def __post_init__(self):
        # Select all variables, that should be a dataclass, but are a dict and
        # turn them into the respective objects
        # pylint: disable=no-member
        objects = {k: v.type(**self.__dict__[k]) for k, v in self.__dataclass_fields__.items()
                   if is_dataclass(v.type) and isinstance(self.__dict__[k], Mapping)}
        self.__dict__.update(objects)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def _handle_db_response(self, response):
        if not response["status"]:
            raise Exception(response["errorMessage"])
        # save pid
        self.pid = response["id"]
