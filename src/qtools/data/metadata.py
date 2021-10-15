from dataclasses import dataclass
from typing import IO

import yaml

from qtools.data.device import Device


@dataclass
class Metadata:
    device: Device

    @classmethod
    def from_yaml(cls, stream):
        data = yaml.load(stream, Loader=yaml.Loader)
        if isinstance(data, Metadata):
            return data
        elif isinstance(data, Device):
            return cls(data)

    def save(self):
        self.device.save()
