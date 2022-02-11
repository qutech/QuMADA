"""
Representations of domain objects (Devices).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from qtools.data.domain import DomainObject
from qtools.data.yaml import DomainYAMLObject


@dataclass
class Factory(DomainObject, DomainYAMLObject):
    """Represents the database entry of a factory."""

    yaml_tag = "!Factory"

    @classmethod
    def create(cls, name: str, **kwargs) -> Factory:
        """Creates a Factory object."""
        kwargs.update({
            "name": name,
        })
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[Factory]:
        return super()._get_all(fn_name="factories")

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateFactory")


@dataclass
class Wafer(DomainObject, DomainYAMLObject):
    """Represents the database entry of a wafer."""

    yaml_tag = "!Wafer"

    description: str
    productionDate: str  # pylint: disable=invalid-name
    factory: Factory

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        productionDate: str,
        factory: Factory,
        **kwargs,
    ) -> Wafer:
        """Creates a Wafer object."""
        kwargs.update(
            {
                "name": name,
                "description": description,
                "productionDate": productionDate,
                "factory": factory,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateWafer")


@dataclass
class Sample(DomainObject, DomainYAMLObject):
    """Represents the database entry of a sample."""

    yaml_tag = "!Sample"

    description: str
    creator: str
    wafer: Wafer
    factory: Factory
    layout: SampleLayout

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        creator: str,
        wafer: Wafer,
        factory: Factory,
        layout: SampleLayout,
        **kwargs,
    ) -> Sample:
        """Creates a Sample object."""
        kwargs.update(
            {
                "name": name,
                "description": description,
                "creator": creator,
                "wafer": wafer,
                "factory": factory,
                "layout": layout,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[Sample]:
        return super()._get_all("samples")

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateSample")


@dataclass
class SampleLayout(DomainObject, DomainYAMLObject):
    """Represents the database entry of a sample layout."""

    yaml_tag = "!SampleLayout"

    mask: str

    @classmethod
    def create(cls, name: str, mask: str, **kwargs) -> SampleLayout:
        """Creates a SampleLayout object."""
        kwargs.update({
            "name": name,
            "mask": mask,
        })
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateSampleLayout")


@dataclass
class Device(DomainObject, DomainYAMLObject):
    """Represents the database entry of a device."""

    yaml_tag = "!Device"

    description: str
    layoutParameters: str  ## pylint: disable=invalid-name
    layout: DeviceLayout
    sample: Sample

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        layoutParameters: str,
        layout: DeviceLayout,
        sample: Sample,
        **kwargs,
    ) -> Device:
        """Creates a Device object."""
        kwargs.update(
            {
                "name": name,
                "description": description,
                "layoutParameters": layoutParameters,
                "layout": layout,
                "sample": sample,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateDevice")


@dataclass
class DeviceLayout(DomainObject, DomainYAMLObject):
    """Represents the database entry of a device layout."""

    yaml_tag = "!DeviceLayout"

    mask: str
    image: str
    creator: str
    gates: list[Gate] = field(default_factory=list)

    # TODO: incorporate gate List
    @classmethod
    def create(
        cls, name: str, mask: str, image: str, creator: str, **kwargs
    ) -> DeviceLayout:
        """Creates a DeviceLayout object."""
        kwargs.update(
            {
                "name": name,
                "mask": mask,
                "image": image,
                "creator": creator,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateDeviceLayout")


@dataclass
class Gate(DomainObject, DomainYAMLObject):
    """Represents the database entry of a gate."""

    yaml_tag = "!Gate"

    function: str
    number: int
    layout: DeviceLayout

    @classmethod
    def create(
        cls, name: str, function: str, number: int, layout: DeviceLayout, **kwargs
    ) -> Gate:
        """Creates a Gate object."""
        kwargs.update(
            {"name": name, "function": function, "number": number, "layout": layout}
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save(fn_name="saveOrUpdateGate")
