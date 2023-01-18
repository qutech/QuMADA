from __future__ import annotations

import numpy as np
from jsonschema import validate
from qcodes.instrument.parameter import Parameter

from qtools.instrument.buffers.buffer import Buffer, BufferException
from qtools.instrument.custom_drivers.ZI.MFLI import MFLI


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
            print("Warning: No trigger threshold specified!")

        self._set_num_points()
        # TODO: This won't work when num_points is passed with settings!
        if all(k in settings for k in ("sampling_rate", "burst_duration", "duration")):
            num_cols = self.num_points
            num_bursts = int(np.ceil(settings["duration"] / settings["burst_duration"]))
            self._daq.count(num_bursts)
            self._daq.duration(settings["burst_duration"])
            self._daq.grid.cols(num_cols)

        if "delay" in settings:
            self._daq.delay(settings["delay"])

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        # TODO: Inform user about automatic changes of settings
        # TODO: This is done BEFORE the setup_buffer, so changes to trigger type will be overriden anyway?
        # print(f"Running trigger setter with: {trigger}")
        if trigger is None:
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
            raise BufferException("Buffer is to small for this measurement. Please reduce the number of data points")
        self._num_points = int(num_points)

    def _set_num_points(self) -> None:
        """
        Calculates number of datapoints and sets
        the num_points accordingly.
        Raises
        ------
        Exception
           Exception if number of points is overdefined.

        Returns
        -------
        None
        """
        if all(k in self.settings for k in ("sampling_rate", "burst_duration", "num_points")):
            raise BufferException("You cannot define sampling_rate, burst_duration and num_points at the same time")
        elif self.settings.get("num_points", False):
            self.num_points = self.settings["num_points"]
        elif all(k in self.settings for k in ("sampling_rate", "burst_duration")):
            self.num_points = int(np.ceil(self.settings["sampling_rate"] * self.settings["burst_duration"]))

    def read(self) -> dict:
        data = self.read_raw()
        result_dict = {}
        # print(f"data = {data}")
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
        for parameter in parameters:
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

    def is_ready(self) -> bool:
        ...

    def is_finished(self) -> bool:
        return self._daq.raw_module.finished()

    def _get_node_from_parameter(self, parameter: Parameter):
        return self._device.demods[self._channel].sample.__getattr__(parameter.signal_name[1])
