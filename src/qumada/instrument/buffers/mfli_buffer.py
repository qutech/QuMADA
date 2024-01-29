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

import logging

import numpy as np
from jsonschema import validate
from qcodes.parameters import Parameter

from qumada.instrument.buffers.buffer import Buffer, BufferException
from qumada.instrument.custom_drivers.ZI.MFLI import MFLI

logger = logging.getLogger(__name__)


class MFLIBuffer(Buffer):
    """Buffer for ZurichInstruments MFLI"""

    AVAILABLE_TRIGGERS: list[str] = [
        "trigger_in_1",
        "trigger_in_2",
        "aux_in_1",
        "aux_in_2",
    ]

    TRIGGER_MODE_MAPPING: dict = {
        "continuous": 0,
        "edge": 1,
        "pulse": 3,
        "tracking_edge": 4,
        "tracking_pulse": 7,
        "digital": 6,
    }

    TRIGGER_MODE_POLARITY_MAPPING: dict = {"positive": 1, "negative": 2, "both": 3}

    GRID_INTERPOLATION_MAPPING: dict = {"nearest": 1, "linear": 2, "exact": 4}
    # TODO: What happens in exact mode? Look up limitations...

    def __init__(self, mfli: MFLI):
        self._session = mfli.session
        self._device = mfli.instr
        self._daq = self._session.modules.daq
        self._sample_nodes: list = []
        self._subscribed_parameters: list[Parameter] = []
        self._trigger: str | None = None
        self._channel = 0
        self._num_points: int | None = None
        self._num_bursts: int = 1
        self._burst_duration: float | None = None

    def setup_buffer(self, settings: dict) -> None:
        # validate settings
        validate(settings, self.settings_schema)
        self.settings: dict = settings
        device = self._device
        self._daq.device(device)

        if "channel" in settings:
            self._channel = settings["channel"]

        device.demods[self._channel].enable(True)

        # TODO: Validate Trigger mode, edge and interpolation!:
        self._daq.type(self.TRIGGER_MODE_MAPPING[settings.get("trigger_mode", "edge")])
        self._daq.edge(self.TRIGGER_MODE_POLARITY_MAPPING[settings.get("trigger_mode_polarity", "positive")])
        self._daq.grid.mode(self.GRID_INTERPOLATION_MAPPING[settings.get("grid_interpolation", "linear")])
        self.trigger = self.trigger  # Don't delete me, I am important!
        if "trigger_threshold" in settings:
            # TODO: better way to distinguish, which trigger level to set
            self._daq.level(settings["trigger_threshold"])
            self._device.triggers.in_[0].level(settings["trigger_threshold"])
            self._device.triggers.in_[1].level(settings["trigger_threshold"])
        else:
            logger.warning("No trigger threshold specified!")
        self._set_num_points()
        self._daq.delay = settings.get("delay", 0)

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        # TODO: Inform user about automatic changes of settings
        # TODO: This is done BEFORE the setup_buffer, so changes to trigger type will be overriden anyway?
        # print(f"Running trigger setter with: {trigger}")
        if trigger is None:
            logger.info("No Trigger provided! Setting trigger to continuous.")
            self._daq.type(0)
        elif trigger in self.AVAILABLE_TRIGGERS:
            samplenode = self._device.demods[self._channel].sample
            if trigger == "trigger_in_1":
                self._daq.triggernode(samplenode.TrigIn1)
                self._daq.type(6)
            elif trigger == "trigger_in_2":
                self._daq.triggernode(samplenode.TrigIn2)
                self._daq.type(6)
            elif trigger == "aux_in_1":
                self._daq.triggernode(samplenode.AuxIn0)
                if self._daq.type() not in (1, 3, 4, 7):
                    self._daq.type(1)
            elif trigger == "aux_in_2":
                self._daq.triggernode(samplenode.AuxIn1)
                if self._daq.type() not in (1, 3, 4, 7):
                    self._daq.type(1)
        else:
            raise BufferException(f"Trigger input '{trigger}' is not supported.")
        self._trigger = trigger

    def force_trigger(self) -> None:
        self._daq.forcetrigger(1)

    @property
    def num_points(self) -> int | None:
        return self._num_points

    @num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 8388608:
            raise BufferException(
                "Buffer is to small for this measurement. \
                                  Please reduce the number of data points"
            )
        self._num_points = int(num_points)

    # TODO: Define setter for other settings (e.g. burst_duration, num_bursts etc)

    def _set_num_points(self) -> None:
        """
        Calculates all required settings for the MFLI and sets the values
        accordingly
        ------
        Exception
           Exception if number of points or number of burst is overdefined.

        Returns
        -------
        None
        """
        # TODO: Include ._daq.repetitions (averages over multiple bursts)

        if all(k in self.settings for k in ("sampling_rate", "burst_duration", "num_points")):
            raise BufferException("You cannot define sampling_rate, burst_duration and num_points at the same time")

        if all(k in self.settings for k in ("sampling_rate", "duration", "num_bursts", "num_points")):
            raise BufferException(
                "You cannot define sampling rate, duration and num_burst and num_points at the same time"
            )

        if all(k in self.settings for k in ("num_bursts", "duration", "burst_duration")):
            raise BufferException("You cannnot define duration, burst_duration and num_bursts at the same time")

        if "burst_duration" in self.settings:
            self._burst_duration = self.settings["burst_duration"]

        if "duration" in self.settings:
            if "burst_duration" in self.settings:
                self._num_bursts = np.ceil(self.settings["duration"] / self._burst_duration)
            elif "num_bursts" in self.settings:
                self._num_bursts = int(self.settings["num_bursts"])
                self._burst_duration = self.settings["duration"] / self._num_bursts
            else:
                logger.info(
                    "You have specified neither burst_duration nor num_bursts. \
                      Using duration as burst_duration!"
                )
                self._burst_duration = self.settings["duration"]

        if "num_points" in self.settings:
            self.num_points = int(self.settings["num_points"])
            if "sampling_rate" in self.settings:
                self._burst_duration = float(self.num_points / self.settings["sampling_rate"])

        elif "sampling_rate" in self.settings:
            self._sampling_rate = float(self.settings["sampling_rate"])
            if self._burst_duration is not None:
                self.num_points = int(np.ceil(self._sampling_rate * self._burst_duration))
            elif all(k in self.settings for k in ("duration", "num_bursts")):
                self._burst_duration = float(self.settings["duration"] / self.settings["num_bursts"])

        self._daq.count(self._num_bursts)
        self._daq.duration(self._burst_duration)
        self._daq.grid.cols(self.num_points)

    def read(self) -> dict:
        data = self.read_raw()
        result_dict = {}
        for parameter in self._subscribed_parameters:
            node = self._get_node_from_parameter(parameter)
            key = next(key for key in data.keys() if str(key) == str(node))
            result_dict[parameter.name] = data[key][0].value
            if "timestamps" not in result_dict:
                result_dict["timestamps"] = data[key][0].time
        return result_dict

    def read_raw(self) -> dict:
        return self._daq.read()

    def subscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters:
            node = self._get_node_from_parameter(parameter)
            if node not in self._sample_nodes:
                self._subscribed_parameters.append(parameter)
                self._sample_nodes.append(node)
                self._daq.subscribe(node)

    def unsubscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters.copy():
            node = self._get_node_from_parameter(parameter)
            if node in self._sample_nodes:
                self._sample_nodes.remove(node)
                self._subscribed_parameters.remove(parameter)
                self._daq.unsubscribe(node)

    def is_subscribed(self, parameter: Parameter) -> bool:
        return parameter in self._subscribed_parameters

    def start(self) -> None:
        self._daq.execute()

    def stop(self) -> None:
        self._daq.raw_module.finish()

    def is_ready(self) -> bool: ...

    def is_finished(self) -> bool:
        return self._daq.raw_module.finished()

    def _get_node_from_parameter(self, parameter: Parameter):
        return self._device.demods[self._channel].sample.__getattr__(parameter.signal_name[1])
