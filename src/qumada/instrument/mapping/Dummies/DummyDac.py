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
    ) -> None:
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

        instrument: DummyDac = instruments.pop()
        assert isinstance(instrument, DummyDac)

        if not start_values:
            start_values = [param.get() for param in parameters]
        ramp_times = [ramp_time for _ in end_values]

        for param, start_value, end_value, ramp_time in zip(parameters, start_values, end_values, ramp_times):
            param._instrument._triggered_ramp(start_value, end_value, ramp_time)

    def setup_trigger_in():
        pass
