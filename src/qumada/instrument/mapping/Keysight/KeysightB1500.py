# -*- coding: utf-8 -*-

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
# - Till Huckeman


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
# - 4K User
# - Daniel Grothe
# - Till Huckeman


from qcodes.instrument.parameter import Parameter

from qcodes.instrument_drivers.Keysight.keysightb1500 import KeysightB1500
from qcodes.instrument_drivers.Keysight.keysightb1500 import constants


from qumada.instrument.mapping.base import InstrumentMapping
from qumada.instrument.mapping import KEYSIGHT_B1500_MAPPING


class KeysightB1500Mapping(InstrumentMapping):
    def __init__(self):
        super().__init__(KEYSIGHT_B1500_MAPPING, is_triggerable=True)
        self._trigger_in: str | None = None
        self.AVAILABLE_TRIGGERS: list = []

    def ramp(
        self,
        parameters: list[Parameter],
        *,
        start_values: list[float] | None = None,
        end_values: list[float],
        ramp_time: float,
        **kwargs,
        #block: bool = False,
        #sync_trigger=None,
    ) -> None:
        smu = self.parameters[0].parent
        n_steps = kwargs.get("n_steps", 501)
        av_coef = kwargs.get("av_coef", 5)
        step_delay=ramp_time/n_steps
        assert len(parameters) == len(end_values)
        if start_values is not None:
            assert len(parameters) == len(start_values)

        if len(parameters) > 1:
            raise Exception("Maximum length of rampable parameters currently is 1.")
        # TODO: Test delay when ramping multiple parameters in parallel.
        # TODO: Add Trigger option?
        # check, if all parameters are from the same instrument
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        instrument: KeysightB1500 = instruments.pop()
        assert isinstance(instrument, KeysightB1500)

        if not start_values:
            start_values = [param.get() for param in parameters]
        # ramp_rates = np.abs((np.array(end_values) - np.array(start_values)) / np.array(ramp_time))
        # if sync_trigger:
        #     if sync_trigger in parameters:
        #         raise Exception("Synchronized trigger cannot be part of parameters")
        #     assert isinstance(sync_trigger.root_instrument, Decadac)
        #     sync_trigger._instrument.enable_ramp(False)
        #     sync_trigger.set(sync_trigger_level)
        for param, start_value, end_value, ramp_time in zip(
            parameters, start_values, end_values, [ramp_time for _ in parameters]
        ):
            smu.setup_staircase_sweep(
                v_src_range = smu._source_config["output_range"],
                v_start = start_value,
                v_end = end_value,
                n_steps = n_steps,
                av_coef = av_coef,
                step_delay = step_delay,
                abort_enabled = constants.Abort.DISABLED,
                i_meas_range = smu._measure_config["i_meas_range"],
                i_comp = smu._source_config["compliance"],
                sweep_mode = constants.SweepMode.LINEAR,
                # and there are more arguments with default values
                # that might need to be changed for your
                # particular measurement situation
            )
#             smu.parent.set_measurement_mode(
#                 mode=constants.MM.Mode.STAIRCASE_SWEEP,
#                 channels=(b1500.smu1.channels[0], b1500.smu2.channels[0])
# )
        #smu.parent.run_iv_staircase_sweep()
        # if sync_trigger:
        #     sync_trigger.set(0)
"""
    def trigger(self, parameter, level=1) -> None:
        instrument: Decadac = parameter.root_instrument
        assert isinstance(instrument, Decadac)
        parameter._instrument.enable_ramp(False)
        parameter.volt.set(level)

    def setup_trigger_in(self, trigger_settings: dict):
        # trigger_dict = {
        #     "always": 0,
        #     "trig1_low": 2,
        #     "trig2_low": 3,
        #     "until_trig1_rising": 4,
        #     "until_trig2_rising": 5,
        #     "until_trig1_falling": 6,
        #     "until_trig2_falling": 7,
        #     "never": 8,
        #     "trig1_high": 10,
        #     "trig2_high": 11,
        #     "after_trig1_rising": 12,
        #     "after_trig2_rising": 13,
        #     "after_trig1_falling": 14,
        #     "after_trig2_falling": 15,
        # }
        # TRIGGER_MODE_MAPPING: dict = {
        #     "continuous": 0,
        #     "edge": 1,
        #     "pulse": 3,
        #     "tracking_edge": 4,
        #     "tracking_pulse": 7,
        #     "digital": 6,
        # }
        print(
            "Warning: The Decadacs trigger level is fixed at roughly 1.69 V and cannot be changed. "
            "Please make sure that your triggers are setup accordingly"
        )
        trigger_mode = trigger_settings.get("trigger_mode", "continuous")
        polarity = trigger_settings.get("trigger_mode_polarity", "positive")

        if (trigger_mode, polarity) == ("edge", "positive"):
            mode = 12
        elif (trigger_mode, polarity) == ("edge", "negative"):
            mode = 14
        elif (trigger_mode, polarity) == ("digital", "positive"):
            mode = 10
        elif (trigger_mode, polarity) == ("digital", "negative"):
            mode = 2
        # TODO: Check other cases
        elif (trigger_mode, polarity) == ("continuous", "positive"):
            mode = 0
        elif (trigger_mode, polarity) == ("continuous", "negative"):
            mode = 0
        else:
            raise Exception("Selected trigger mode is not supported by DecaDac")

        if self.trigger_in is None:
            mode = 0
            print("No trigger input selected. Using continuous acquisition")
        if self.trigger_in == "trigger_in_2":
            mode += 1

        self.trigger_mode = mode

    @property
    def trigger_in(self):
        return self._trigger_in

    @trigger_in.setter
    def trigger_in(self, trigger: str | None) -> None:
        # TODO: Inform user about automatic changes of settings
        # TODO: This is done BEFORE the setup_buffer, so changes to trigger type will be overriden anyway?
        # print(f"Running trigger setter with: {trigger}")
        if trigger in self.AVAILABLE_TRIGGERS:
            self._trigger_in = trigger
        else:
            raise Exception(f"Trigger input {trigger} not available")
        if trigger is None:
            print("No Trigger provided!")

"""