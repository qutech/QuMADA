#!/usr/bin/env python3
"""
General Object class for the domain.
"""

import json
from dataclasses import dataclass

@dataclass
class DomainObject:
    pid: str
    name: str
    creatorId: str
    createDate: str
    lastChangerId: str
    lastChangeDate: str

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__