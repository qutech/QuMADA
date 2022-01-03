from dataclasses import dataclass
from typing import Iterable

import yaml

from qtools.data.device import Device
from qtools.data.domain import DomainObject
from qtools.data.measurement import Experiment, Measurement


@dataclass
class Metadata(yaml.YAMLObject):
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
        def recurse(node: Iterable[DomainObject]):
            for domain_object in node:
                sublist = []
                for v in domain_object.__dict__.values():
                    if isinstance(v, DomainObject):
                        sublist.append(v)
                    elif isinstance(v, Iterable):
                        # TODO: I'm ugly, please make me prettier
                        ssl = [o for o in v if isinstance(o, DomainObject)]
                        sublist.extend(ssl)
                if sublist:
                    recurse(sublist)
                try:
                    domain_object.save()
                except AttributeError:
                    # No save function
                    pass

        recurse([self.measurement])
