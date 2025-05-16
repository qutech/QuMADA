# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Till Huckemann


from __future__ import annotations

from qcodes.parameters import Parameter

from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qumada.instrument.mapping import DUMMY_DAC_MAPPING
from qumada.instrument.mapping.base import InstrumentMapping


class DummyDacMapping(InstrumentMapping):
    def __init__(self):
        super().__init__(DUMMY_DAC_MAPPING)

    def ramp(
        self,
        parameters: list[Parameter],
        *,
        start_values: list[float] | None = None,
        end_values: list[float],
        ramp_time: float,
        **kwargs,
    ) -> None:
        num_points = kwargs.get("num_points", 100 * ramp_time)
        assert len(parameters) == len(end_values)
        if start_values is not None:
            assert len(parameters) == len(start_values)

        if len(parameters) > 4:
            raise Exception("Maximum length of rampable parameters currently is 4.")
        # TODO: Test delay when ramping multiple parameters in parallel.
        # TODO: Add Trigger option?
        # check, if all parameters are from the same instrument
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        instrument: DummyDac = instruments.pop()
        assert isinstance(instrument, DummyDac)

        if not start_values:
            start_values = [param.get() for param in parameters]

        instrument._triggered_ramp_channels(
            [param._instrument for param in parameters], start_values, end_values, ramp_time, num_points
        )

    def pulse(
        self,
        parameters: list[Parameter],
        *,
        setpoints: list[list[float]],
        delay: float,
        sync_trigger=None,
        **kwargs,
    ) -> None:
        assert len(parameters) == len(setpoints)
        num_points = len(setpoints[0])
        for setpoint in setpoints:
            assert len(setpoint) == num_points

        duration = num_points * delay
        if len(parameters) > 4:
            raise Exception("Maximum length of pulsable parameters currently is 4.")
        # TODO: Test delay when ramping multiple parameters in parallel.
        # TODO: Add Trigger option?
        # check, if all parameters are from the same instrument
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        instrument: DummyDac = instruments.pop()
        assert isinstance(instrument, DummyDac)
        instrument._triggered_pulse_channels([param._instrument for param in parameters], setpoints, duration)

    def setup_trigger_in():
        pass
