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
# - Bertha Lab Setup
# - Daniel Grothe
# - Till Huckeman

import logging
from qcodes.parameters import Parameter
from qcodes_contrib_drivers.drivers.QDevil.QDAC2 import QDac2

from qumada.instrument.mapping import QDAC2_MAPPING
from qumada.instrument.mapping.base import InstrumentMapping

logger = logging.getLogger(__name__)

class QDac2Mapping(InstrumentMapping):
    def __init__(self):
        super().__init__(QDAC2_MAPPING)

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

        points=kwargs.get("num_points", int(ramp_time*1000))
        wait_time=ramp_time/points

        assert len(parameters) == len(end_values)
        for parameter in parameters:
            assert parameter._short_name == "dc_constant_V"
        
        if start_values is not None:
            assert len(parameters) == len(start_values)

        if len(parameters) > 8:
            raise Exception("Maximum length of rampable parameters is 8.")

        # check, if all parameters are from the same instrument
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        qdac: QDac2 = instruments.pop()
        assert isinstance(qdac, QDac2)

        if not start_values:
            start_values = [param.dc_constant_V() for param in parameters]
        
        channels = [param._instrument for param in parameters]
        for channel, start, stop in zip(channels, start_values, end_values):
            dc_sweep = channel.dc_sweep(
                        start_V=start,
                        stop_V=stop, 
                        points=points,
                        dwell_s=wait_time,
                        backwards=(start>stop))
            # There appears to be a bug with the built in dc_sweep of the QDAC!
            # The sweep direction is always from the lower to the large value if
            # backwards==False and the other way round if it is true.
            # Once this is fixed, remove the backwards argument from function call!

        if sync_trigger is not None:
            if sync_trigger in range(1, 6):
                trigger = dc_sweep.start_marker()
                qdac.external_triggers[sync_trigger-1].width_s(1e-3)
                qdac.external_triggers[sync_trigger-1].polarity('norm')
                qdac.external_triggers[sync_trigger-1].source_from_trigger(trigger)
            else:
                logger.warning(f"{sync_trigger} is no valid sync trigger for QDac II. Choose an integer between 1 and 5!")

        qdac.start_all()
        
        
    def pulse(
        self,
        parameters: list[Parameter],
        *,
        setpoints: list[list[float]],
        delay: float,
        sync_trigger=None,
        **kwargs,
    ) -> None:
        # Make sure everything is in order...
        assert len(parameters) == len(setpoints)
        for points in setpoints:
            assert len(points) == len(setpoints[0])
            for parameter in parameters:
                assert parameter._short_name == "dc_constant_V"
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. \
                This would lead to non synchronized ramps.")
        qdac: QDac2 = instruments.pop()
        assert isinstance(qdac, QDac2)
        channels = [param._instrument for param in parameters]
        for channel, points in zip(channels, setpoints):
            dc_list = channel.dc_list(
                voltages = points,
                dwell_s = delay,
            )

        if sync_trigger is not None:
            if sync_trigger in range(1, 6):
                trigger = dc_list.start_marker()
                qdac.external_triggers[sync_trigger-1].width_s(1e-3)
                qdac.external_triggers[sync_trigger-1].polarity('norm')
                qdac.external_triggers[sync_trigger-1].source_from_trigger(trigger)
            else:
                logger.warning(f"{sync_trigger} is no valid sync trigger for QDac II. Choose an integer between 1 and 5!")
        qdac.start_all()

    def setup_trigger_in():
        raise Exception("QDac2 does not have a trigger input \
            not yet supported!")
