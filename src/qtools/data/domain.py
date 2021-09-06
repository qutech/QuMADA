#!/usr/bin/env python3
"""
General Object class for the domain.
"""

from collections.abc import Mapping
import json
from dataclasses import dataclass, is_dataclass
from sqlite3 import DatabaseError


@dataclass
class DomainObject:
    """Represents a database entry. Consists of the data fields, every db entry has."""
    pid: str
    name: str
    creatorId: str
    createDate: str
    lastChangerId: str
    lastChangeDate: str

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
            raise DatabaseError(response["errorMessage"])
        # save pid
        self.pid = response["id"]

