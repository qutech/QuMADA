from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Callable
from pyvisa import VisaIOError

from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from zhinst.toolkit.driver.devices import DeviceType
from zhinst.toolkit.session import Session

from qcodes.instrument_drivers.stanford_research.SR830 import SR830


def is_instrument_class(o):
    """True, if class is of type Instrument or a subclass of Instrument"""
    return inspect.isclass(o) and issubclass(o, Instrument)


class BufferException(Exception):
    """General Buffer Exception"""


class Buffer(ABC):
    """Base class for a general buffer interface for an instrument."""

    SETTING_NAMES: set[str] = {
        "trigger_type",
        "trigger_threshold",
        "delay",
        "num_points",
        "channel",
        "sample_rate",
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

    @abstractmethod
    def start(self) -> None:
        """Start the buffer. This is not the trigger."""

    def stop(self) -> None:
        """Stop the buffer."""


class SoftwareTrigger(Parameter):
    def __init__(self, **kwargs):
        self._triggers = []
        super().__init__(**kwargs)
    
    def add_trigger(self, callable: Callable):
        self._triggers.append(callable)



class SR830Buffer(Buffer):
    class ExternalTrigger(Parameter):
        ...

    def __init__(self, device: SR830):
        self._device = device
        self._trigger = None
        self._subscribed_channels = set()

    def setup_buffer(self, settings: dict | None = None) -> None:
        """Sets instrument related settings for the buffer."""
        # TODO: sample_rate mit delay und num_points abgleichen
        # TODO: Trigger und SR abgleichen
        if not settings:
            settings = {}

        self._device.buffer_SR(settings.setdefault("sample_rate", 512))
        self._device.buffer_trig_mode("OFF")

    @property  # type: ignore
    def trigger(self) -> Any:
        return self._trigger

    @trigger.setter  # type: ignore
    def trigger(self, parameter: Parameter) -> None:
        if isinstance(parameter, SoftwareTrigger):
            parameter.add_trigger(self._device.send_trigger)
        if isinstance(parameter, (SR830Buffer.ExternalTrigger, SoftwareTrigger)):
            self._device.buffer_SR("Trigger")
            self._device.buffer_trig_mode("On")
        else:
            raise BufferException("SR830 does not support setting custom trigger inputs. Use SoftwareTrigger or SR830Buffer.ExternalTrigger and the input on the back of the unit.")

    def read(self) -> dict:
        #TODO: Handle stopping buffer or not
        data = {}
        try:
            for ch in self._subscribed_channels:
                data[ch] = self._device.__getattr__(f"{ch}_datatrace").get()
        except VisaIOError as ex:
            raise BufferException("Could not read the buffer. Buffer has to be stopped before readout.")
        return data

    def subscribe(self, parameters: list[Parameter]) -> None:

        for parameter in parameters:
            name = parameter.name
            if name in ["X", "R", "X Noise", "aux_in1", "aux_in2"]:
                self._device.ch1_display(name)
                self._subscribed_channels.add("ch1")
            elif name in ["Y", "Phase", "Y Noise", "aux_in3", "aux_in4"]:
                self._device.ch2_display(name)
                self._subscribed_channels.add("ch2")
            else:
                raise Exception(f"Parameter {parameter.name} can not be buffered.")

    def unsubscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters:
            name = parameter.name
            if name in ["X", "R", "X Noise", "aux_in1", "aux_in2"]:
                self._subscribed_channels.remove("ch1")
            elif name in ["Y", "Phase", "Y Noise", "aux_in3", "aux_in4"]:
                self._subscribed_channels.remove("ch2")
            else:
                raise Exception(f"Parameter {parameter.name} can not be buffered.")

    def start(self) -> None:
        self._device.buffer_reset()
        self._device.buffer_start()
    
    def stop(self) -> None:
        self._device.buffer_pause()


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

    def subscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters:
            node = self._device.demods[self._channel].sample.__getattr__(parameter.name)
            if node not in self._sample_nodes:
                self._sample_nodes.append(node)
                self._daq.subscribe(node)

    def unsubscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters:
            node = self._device.demods[self._channel].sample.__getattr__(parameter.name)
            if node in self._sample_nodes:
                self._sample_nodes.remove(node)
                self._daq.unsubscribe(node)
