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
# - Bertha Lab Setup
# - Daniel Grothe
# - Till Huckeman


from qcodes.parameters import Parameter
from qcodes_contrib_drivers.drivers.QDevil.QDAC1 import QDac

from qumada.instrument.mapping import QDAC_MAPPING
from qumada.instrument.mapping.base import InstrumentMapping


class QDacMapping(InstrumentMapping):
    def __init__(self):
        super().__init__(QDAC_MAPPING)
        self.max_ramp_channels = 8
    def ramp(
        self,
        parameters: list[Parameter],
        *,
        start_values: list[float] | None = None,
        end_values: list[float],
        ramp_time: float,
        sync_trigger=None,
        **kwargs,
    ) -> None:
        assert len(parameters) == len(end_values)
        if start_values is not None:
            assert len(parameters) == len(start_values)

        if len(parameters) > 8:
            raise Exception("Maximum length of rampable parameters is 8.")

        # check, if all parameters are from the same instrument
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        instrument: QDac = instruments.pop()
        assert isinstance(instrument, QDac)

        channellist = [instrument.channels.index(param._instrument) + 1 for param in parameters]

        if not start_values:
            start_values = []
        if sync_trigger is not None:
            parameters[0]._instrument.sync(sync_trigger)

        instrument.ramp_voltages(
            channellist=channellist,
            v_startlist=start_values,
            v_endlist=end_values,
            ramptime=ramp_time,
        )
        parameters[0]._instrument.sync(0)

    def setup_trigger_in(self):
        raise Exception("QDac does not have a trigger input!")
        
    def force_trigger(self):
        pass
        # Not required as QDac has no trigger input and starts ramps instantly.
