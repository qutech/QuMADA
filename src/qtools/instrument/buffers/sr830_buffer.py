from __future__ import annotations

import numpy as np
from jsonschema import validate
from pyvisa import VisaIOError
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.parameters import Parameter

from qtools.instrument.buffers.buffer import Buffer, BufferException


class SR830Buffer(Buffer):
    """Buffer for Stanford SR830"""

    ch1_names = ["X", "R", "X Noise", "aux_in1", "aux_in2"]
    ch2_names = ["Y", "Phase", "Y Noise", "aux_in3", "aux_in4"]

    AVAILABLE_TRIGGERS: list[str] = ["external"]

    def __init__(self, device: SR830):
        self._device = device
        self._trigger: str | None = None
        self._subscribed_parameters: set[Parameter] = set()
        self._num_points: int | None = None

    def setup_buffer(self, settings: dict) -> None:
        """Sets instrument related settings for the buffer."""
        # TODO: Validation for sampling rates (look up in manual) Comment: Is this required? Is handled by driver...
        # TODO: Trigger und SR abgleichen
        # TODO: Are there different trigger modes?

        validate(settings, self.settings_schema)
        self.settings: dict = settings
        self._device.buffer_SR(settings.get("sampling_rate", 512))
        self._device.buffer_trig_mode("OFF")
        self._set_num_points()
        self.delay_data_points = 0  # Datapoints to delete at the beginning of dataset due to delay.
        self.delay = settings.get("delay", 0)
        if self.delay < 0:
            raise BufferException("The SR830'S Trigger Input does not support negative delays.")
        else:
            self.delay_data_points = int(self.delay * self._device.buffer_SR())
            self.num_points = self.delay_data_points + self.num_points
            # TODO: There has to be a more elegant way for the setter.

    @property
    def num_points(self) -> int | None:
        return self._num_points

    @num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 16383:
            raise BufferException(
                "SR830 is to small for this measurement. Please reduce the number of data points or the delay"
            )
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
            if self.settings.get("sampling_rate", False):
                self._device.buffer_SR(self.settings["sampling_rate"])
            else:
                self._device.buffer_SR(self.num_points / self.settings["burst_duration"])
        elif all(k in self.settings for k in ("sampling_rate", "burst_duration")):
            self.num_points = int(np.ceil(self.settings["sampling_rate"] * self.settings["burst_duration"]))

    @property
    def trigger(self) -> str | None:
        return self._trigger

    @trigger.setter
    def trigger(self, trigger: str | None) -> None:
        if trigger is None:
            # TODO: standard value for Sample Rate
            self._device.buffer_SR(512)
            self._device.buffer_trig_mode("OFF")
        elif trigger == "external":
            self._device.buffer_SR("Trigger")
            self._device.buffer_trig_mode("ON")
        else:
            raise BufferException(
                "SR830 does not support setting custom trigger inputs. Use 'external' and the input on the back of the unit."
            )
        self._trigger = trigger

    def force_trigger(self) -> None:
        self._device.buffer_start()

    def read_raw(self) -> dict:
        # TODO: Handle stopping buffer or not
        data = {}
        try:
            for parameter in self._subscribed_parameters:
                if parameter.name in self.ch1_names:
                    ch = "ch1"
                elif parameter.name in self.ch2_names:
                    ch = "ch2"

                # TODO: what structure has the data? do we get timestamps?
                data[parameter.name] = self._device.__getattr__(f"{ch}_datatrace").get()
                data[parameter.name] = data[parameter.name][self.delay_data_points : self.num_points]
        except VisaIOError as ex:
            raise BufferException("Could not read the buffer. Buffer has to be stopped before readout.") from ex
        return data

    def read(self) -> dict:
        # TODO: Add timetrace if possible
        return self.read_raw()

    def subscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters:
            name = parameter.name
            if name in self.ch1_names:
                self._device.ch1_display(name)
                param_to_remove = {param for param in self._subscribed_parameters if param.name in self.ch1_names}
                self._subscribed_parameters.difference_update(
                    param_to_remove
                )  # remove previously subscribed parameter from ch1
                self._subscribed_parameters.add(parameter)
            elif name in self.ch2_names:
                self._device.ch2_display(name)
                param_to_remove = {param for param in self._subscribed_parameters if param.name in self.ch2_names}
                self._subscribed_parameters.difference_update(
                    param_to_remove
                )  # remove previously subscribed parameter from ch2
                self._subscribed_parameters.add(parameter)
            else:
                raise BufferException(f"Parameter {parameter.name} can not be buffered.")

    def unsubscribe(self, parameters: list[Parameter]) -> None:
        for parameter in parameters.copy():
            name = parameter.name
            if name in ["X", "R", "X Noise", "aux_in1", "aux_in2"]:
                self._subscribed_parameters.remove(parameter)
            elif name in ["Y", "Phase", "Y Noise", "aux_in3", "aux_in4"]:
                self._subscribed_parameters.remove(parameter)
            else:
                raise BufferException(f"Parameter {parameter.name} can not be buffered.")

    def is_subscribed(self, parameter: Parameter) -> bool:
        return parameter in self._subscribed_parameters

    def start(self) -> None:
        self._device.buffer_reset()
        self._device.buffer_start()

    def stop(self) -> None:
        self._device.buffer_pause()

    def is_ready(self) -> bool:
        ...

    def is_finished(self) -> bool:
        if self._device.buffer_npts() >= self.num_points:
            self.stop()
            return True
        else:
            return False
