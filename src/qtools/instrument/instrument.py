import inspect
from abc import ABC, abstractmethod
from typing import Any

from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from zhinst.toolkit.driver.devices import DeviceType
from zhinst.toolkit.session import Session


def is_instrument_class(o):
    """True, if class is of type Instrument or a subclass of Instrument"""
    return inspect.isclass(o) and issubclass(o, Instrument)


class Buffer(ABC):
    """Base class for a general buffer interface for an instrument."""

    SETTING_NAMES: set[str] = {
        "trigger_type",
        "trigger_threshold",
        "delay",
        "num_points",
        "channel",
    }

    @abstractmethod
    def setup_buffer(self, settings: dict) -> None:
        """Sets instrument related settings for the buffer."""

    @property  # type: ignore
    @abstractmethod
    def trigger(self) -> Any:
        """
        The parameter, that triggers the instruments buffer.
        Set the trigger parameter using a qcodes parameter.
        """

    @trigger.setter  # type: ignore
    @abstractmethod
    def trigger(self, parameter: Parameter) -> None:
        ...

    @abstractmethod
    def read(self) -> dict:
        """Read the buffer."""

    @abstractmethod
    def subscribe(self, *parameters: list[Parameter]) -> None:
        """Measure provided parameters with the buffer."""

    @abstractmethod
    def unsubscribe(self, *parameters: list[Parameter]) -> None:
        """Unsubscribe provided parameters, if they were subscribed."""


class MFLIBuffer(Buffer):
    def __init__(self, session: Session, device: DeviceType):
        self._session = session
        self._device = device
        self._daq = session.modules.daq
        self._sample_nodes = []
        self._channel = 0

    def setup_buffer(self, settings: dict) -> None:
        device = self._device
        self._daq.device(device)

        if "channel" in settings:
            self._channel = settings["channel"]

        device.demods[self._channel].enable(True)

        self._daq.type(settings.setdefault("trigger_type", 2))

    @property
    def trigger(self):
        return super().trigger

    @trigger.setter
    def trigger(self, parameter: Parameter) -> None:
        ...

    def read(self) -> dict:
        return self._daq.read()

    def subscribe(self, *parameters: list[Parameter]) -> None:
        for parameter in parameters:
            node = self._device.demods[self._channel].sample.__getattr__(parameter.name)
            if node not in self._sample_nodes:
                self._sample_nodes.append(node)
                self._daq.subscribe(node)

    def unsubscribe(self, *parameters: list[Parameter]) -> None:
        for parameter in parameters:
            node = self._device.demods[self._channel].sample.__getattr__(parameter.name)
            if node in self._sample_nodes:
                self._sample_nodes.remove(node)
                self._daq.unsubscribe(node)
