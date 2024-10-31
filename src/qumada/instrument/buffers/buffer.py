# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Till Huckeman

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from qcodes.instrument import Instrument
from qcodes.metadatable import Metadatable
from qcodes.parameters import Parameter

logger = logging.getLogger(__name__)




def is_bufferable(object: Instrument | Parameter):
    """Checks if the instrument or parameter is bufferable using the qumada Buffer definition."""
    if isinstance(object, Parameter):
        object = object.root_instrument
    return hasattr(object, "_qumada_buffer")  # and isinstance(object._qumada_buffer, Buffer)
    # TODO: check, if parameter can really be buffered
    # TODO: For some reason checking the type doesn't work all the time. Check again later.


def is_triggerable(object: Instrument | Parameter):
    """
    Checks if the instrument or parameter can be triggered by checking the corresponding flag in
    the mapping
    """
    if isinstance(object, Parameter):
        object = object.root_instrument
    return object._is_triggerable


class BufferException(Exception):
    """General Buffer Exception"""


def map_buffers(
    components: Mapping[Any, Metadatable],
    skip_mapped=True,
    **kwargs,
) -> None:
    """
    Maps the bufferable instruments of gate parameters.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
    """

    buffered_instruments = filter(is_bufferable, components.values())
    for instrument in buffered_instruments:
        buffer = instrument._qumada_buffer
        if skip_mapped:
            if buffer.trigger in buffer.AVAILABLE_TRIGGERS:
                return
        print("Available trigger inputs:")
        print("[0]: None")
        for idx, trigger in enumerate(buffer.AVAILABLE_TRIGGERS, 1):
            print(f"[{idx}]: {trigger}")
        chosen = int(input(f"Choose the trigger input for {instrument.name}: "))
        if chosen == 0:
            trigger = None
        else:
            trigger = buffer.AVAILABLE_TRIGGERS[chosen - 1]
        buffer.trigger = trigger
        print(f"{buffer.trigger=}")


def _map_triggers(
    components: Mapping[Any, Metadatable],
    skip_mapped=True,
    **kwargs,
) -> None:
    """
    Maps the bufferable instruments of gate parameters.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
    """
    triggered_instruments = filter(is_triggerable, components.values())
    for instrument in triggered_instruments:
        if skip_mapped:
            if instrument._qumada_mapping.trigger_in in instrument._qumada_mapping.AVAILABLE_TRIGGERS:
                return
        print("Available trigger inputs:")
        print("[0]: None")
        for idx, trigger in enumerate(instrument._qumada_mapping.AVAILABLE_TRIGGERS, 1):
            print(f"[{idx}]: {trigger}")
        chosen = int(input(f"Choose the trigger input for {instrument.name}: "))
        if chosen == 0:
            trigger = None
        else:
            trigger = instrument._qumada_mapping.AVAILABLE_TRIGGERS[chosen - 1]
        instrument._qumada_mapping.trigger_in = trigger
        print(f"trigger input = {instrument._qumada_mapping.trigger_in}")


def map_triggers(
    components: Mapping[Any, Metadatable],
    skip_mapped=True,
    path: None | str = None,
    **kwargs,
) -> None:
    """
    Maps the triggers of triggerable or bufferable components.
    Ignores already mapped triggers by default.

    Parameters
    ----------
    components : Mapping[Any, Metadatable]
        Components of QCoDeS station (containing instruments to be mapped).
    properties : dict
        Properties of measurement script/device. Currently only required for
        buffered instruments.
        TODO: Remove!
    gate_parameters : Mapping[Any, Mapping[Any, Parameter] | Parameter]
        Parameters of measurement script/device. Currently only required for
        buffered instruments.
        TODO: Remove!
    skip_mapped : Bool, optional
        If true already mapped parameters are skipped
        Set to false if you want to remap something. The default is True.
    path : None|str, optional
        Provide path to a json file with trigger mapping. If not all instruments
        are covered in the file, you will be asked to map those. Works only if
        names in file match instrument.full_name of your current instruments.
        The default is None.
    """
    if path is not None:
        try:
            load_trigger_mapping(components, path)
        except Exception as e:
            logger.warning(f"Exception when loadig trigger mapping from file: {e}")
    map_buffers(
        components,
        skip_mapped,
        **kwargs,
    )
    _map_triggers(components, skip_mapped, **kwargs)


def save_trigger_mapping(components: Mapping[Any, Metadatable], path: str):
    """
    Saves mapped triggers from components to json file.
    Components should be station.components, path is the path to the file.
    """
    trigger_dict = {}
    triggered_instruments = filter(lambda x: any((is_triggerable(x), is_bufferable(x))), components.values())
    for instrument in triggered_instruments:
        try:
            trigger_dict[instrument.full_name] = instrument._qumada_mapping.trigger_in
        except AttributeError:
            trigger_dict[instrument.full_name] = instrument._qumada_buffer.trigger
    with open(path, mode="w") as file:
        json.dump(trigger_dict, file)


def load_trigger_mapping(components: Mapping[Any, Metadatable], path: str):
    """
    Loads json file with trigger mappings and tries to apply them to instruments
    in the components. Works only if the instruments have the same full_name
    as in the saved file!
    """
    with open(path) as file:
        trigger_dict: Mapping[str, Mapping[str, str] | str] = json.load(file)
    for instrument_name, trigger in trigger_dict.items():
        for instrument in components.values():
            if instrument.full_name == instrument_name:
                if is_bufferable(instrument) is True:
                    instrument._qumada_buffer.trigger = trigger
                elif is_triggerable(instrument) is True:
                    instrument._qumada_mapping.trigger_in = trigger


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
    def trigger(self, parameter: Parameter | None) -> None: ...

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
    def num_points(self) -> None: ...

    @abstractmethod
    def force_trigger(self) -> None:
        """Triggers the trigger."""

    @abstractmethod
    def read(self) -> dict:
        """
        Read the buffer

        Output is a dict with the following structure:

        .. code-block:: python

            {
                "timestamps": list[float],
                "param1": list[float],
                "param2": list[float],
                ...
            }

        """

    @abstractmethod
    def read_raw(self) -> Any:
        """Read the buffer and return raw output."""

    @abstractmethod
    def subscribe(self, parameters: set | list[Parameter]) -> None:
        """Measure provided parameters with the buffer."""

    @abstractmethod
    def unsubscribe(self, parameters: set | list[Parameter]) -> None:
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
