"""
Measurement metadata
"""
from dataclasses import dataclass
from typing import Iterable

import yaml

from qtools.data.domain import DomainObject
from qtools.data.measurement import Measurement


@dataclass
class Metadata(yaml.YAMLObject):
    """
    This metadata object can by loaded from YAML and it's content can be saved to the database.
    """
    yaml_tag = "!Metadata"

    measurement: Measurement

    @classmethod
    def from_yaml(cls, stream):
        data = yaml.load(stream, Loader=yaml.Loader)
        if isinstance(data, Metadata):
            return data
        else:
            raise ValueError("Metadata file does not contain a metadata object.")

    def save_to_db(self):
        """Save the measurement metadata to the database."""
        def recurse(node: Iterable[DomainObject]):
            for domain_object in node:
                sublist = []
                for value in domain_object.__dict__.values():
                    if isinstance(value, DomainObject):
                        sublist.append(value)
                    elif isinstance(value, Iterable):
                        # TODO: I'm ugly, please make me prettier
                        ssl = [o for o in value if isinstance(o, DomainObject)]
                        sublist.extend(ssl)
                if sublist:
                    recurse(sublist)
                try:
                    domain_object.save()
                except AttributeError:
                    # No save function
                    pass

        recurse([self.measurement])
