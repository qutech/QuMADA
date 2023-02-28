from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from qcodes.instrument import Instrument
from qcodes.metadatable import Metadatable
from qcodes.parameters import Parameter


def is_bufferable(object: Instrument | Parameter):
    """Checks if the instrument or parameter is bufferable using the qtools Buffer definition."""
    if isinstance(object, Parameter):
        object = object.root_instrument
    return hasattr(object, "_qtools_buffer") and isinstance(object._qtools_buffer, Buffer)
    # TODO: check, if parameter can really be buffered


class BufferException(Exception):
    """General Buffer Exception"""


def map_buffers(
    components: Mapping[Any, Metadatable],
    properties: dict,
    gate_parameters: Mapping[Any, Mapping[Any, Parameter] | Parameter],
    overwrite_trigger=None,
    skip_mapped = True,
) -> None:
    """
    Maps the bufferable instruments of gate parameters.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Gates, as defined in the measurement script
    """
    # subscribe to gettable parameters with buffer
    for gate, parameters in gate_parameters.items():
        for parameter, channel in parameters.items():
            if properties[gate][parameter]["type"] == "gettable":
                if is_bufferable(channel):
                    buffer: Buffer = channel.root_instrument._qtools_buffer
                    buffer.subscribe([channel])

    buffered_instruments = filter(is_bufferable, components.values())
    for instrument in buffered_instruments:
        buffer = instrument._qtools_buffer
        if skip_mapped:
            if buffer.trigger in buffer.AVAILABLE_TRIGGERS:
                return 
        print("Available trigger inputs:")
        print("[0]: None")
        for idx, trigger in enumerate(buffer.AVAILABLE_TRIGGERS, 1):
            print(f"[{idx}]: {trigger}")
        # TODO: Just a workaround, fix this!
        if overwrite_trigger is not None:
            try:
                chosen = int(overwrite_trigger)
            except:
                chosen = int(input(f"Choose the trigger input for {instrument.name}: "))
        else:
            chosen = int(input(f"Choose the trigger input for {instrument.name}: "))
        if chosen == 0:
            trigger = None
        else:
            trigger = buffer.AVAILABLE_TRIGGERS[chosen - 1]
        buffer.trigger = trigger
        print(f"{buffer.trigger=}")


class Buffer(ABC):
    """Base class for a general buffer interface for an instrument."""

    SETTING_NAMES: set[str] = {
        "trigger_mode",
        "trigger_threshold",
        "delay",
        "num_points",
        "channel",  # TODO: Remove? Should be part of the mapping.
        "sampling_rate",
        "duration",
        "burst_duration",
        "grid_interpolation",
        "num_bursts",
    }

    TRIGGER_MODE_NAMES: list[str] = [
        "continuous",
        "edge",
        "tracking_edge",
        "pulse",
        "tracking_pulse",
        "digital",
    ]

    TRIGGER_MODE_POLARITY_NAMES: list[str] = [
        "positive",
        "negative",
        "both",
    ]

    GRID_INTERPOLATION_NAMES: list[str] = [
        "exact",
        "nearest",
        "linear",
    ]

    AVAILABLE_TRIGGERS: list[str] = []

    settings_schema = {
        "type": "object",
        "properties": {
            "trigger_mode": {"type": "string", "enum": TRIGGER_MODE_NAMES},
            "trigger_mode_polarity": {
                "type": "string",
                "enum": TRIGGER_MODE_POLARITY_NAMES,
            },
            "grid_interpolation": {"type": "string", "enum": GRID_INTERPOLATION_NAMES},
            "trigger_threshold": {"type": "number"},
            "delay": {"type": "number"},
            "num_points": {"type": "integer"},
            "channel": {"type": "integer"},
            "sampling_rate": {"type": "number"},
            "duration": {"type": "number"},
            "burst_duration": {"type": "number"},
            "num_bursts": {"type": "integer"},
        },
        "oneOf": [
            {
                "required": ["sampling_rate", "duration"],
                "not": {"required": ["num_points"]},
            },
            {
                "required": ["sampling_rate", "num_points"],
                "not": {"required": ["duration"]},
            },
            {
                "required": ["duration", "num_points"],
                "not": {"required": ["sampling_rate"]},
            },
        ],
        "additionalProperties": False,
    }

    @abstractmethod
    def setup_buffer(self, settings: dict) -> None:
        """Sets instrument related settings for the buffer."""

    @property  # type: ignore
    @abstractmethod
    def trigger(self) -> Parameter | None:
        """
        The parameter, that triggers the instruments buffer.
        Set the trigger parameter using a qcodes parameter.
        """

    @trigger.setter  # type: ignore
    @abstractmethod
    def trigger(self, parameter: Parameter | None) -> None:
        ...

    @property
    @abstractmethod
    def num_points(self) -> int | None:
        """
        Number of points to write into buffer for each burst.
        Required to setup qcodes datastructure and to compare with max. buffer length.
        """
        # TODO: Handle multiple bursts

    @num_points.setter
    @abstractmethod
    def num_points(self) -> None:
        ...

    @abstractmethod
    def force_trigger(self) -> None:
        """Triggers the trigger."""

    @abstractmethod
    def read(self) -> dict:
        """
        Read the buffer

        Output is a dict with the following structure:

        {
            timestamps: list[float],
            param1: list[float],
            param2: list[float],
            ...
        }"""

    @abstractmethod
    def read_raw(self) -> Any:
        "Read the buffer and return raw output."

    @abstractmethod
    def subscribe(self, parameters: list[Parameter]) -> None:
        """Measure provided parameters with the buffer."""

    @abstractmethod
    def unsubscribe(self, parameters: list[Parameter]) -> None:
        """Unsubscribe provided parameters, if they were subscribed."""

    @abstractmethod
    def is_subscribed(self, parameter: Parameter) -> bool:
        """True, if the parameter is subscribed and saved in buffer."""

    @abstractmethod
    def start(self) -> None:
        """Start the buffer. This is not the trigger."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the buffer."""

    @abstractmethod
    def is_ready(self) -> bool:
        """True, if buffer is correctly initialized and ready to measure."""

    @abstractmethod
    def is_finished(self) -> bool:
        """True, if measurement is done and data has finished reading from the buffer."""


# class SoftwareTrigger(Parameter):
#     def __init__(self, **kwargs):
#         self._triggers = []
#         super().__init__(**kwargs)

#     def add_trigger(self, callable: Callable):
#         self._triggers.append(callable)

# TODO: Put buffer classes in separate files? Might become a bit crowded here in the future...
