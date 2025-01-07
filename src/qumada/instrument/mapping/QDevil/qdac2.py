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

from qumada.instrument.custom_drivers.QDevil.QDAC2 import QDac2
from qumada.instrument.mapping import QDAC2_MAPPING
from qumada.instrument.mapping.base import InstrumentMapping

logger = logging.getLogger(__name__)


class QDac2Mapping(InstrumentMapping):
    def __init__(self):
        super().__init__(QDAC2_MAPPING)
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
        """
        Qumada ramp method using the QDacII dc_sweep to ramp smoothly.
            parameters: List of parameters to be set.
                        Elements have to be from the same QDACII
            start_values:  List of start values for the parameters (optional).
                        Current value will be used if None.
            stop_values: List of end values for the parameters.
            delay:      Time in between to setpoints in s. Has to be >=1e-6 s
            sync_trigger [int|None]: Ext Trigger output (1-6) to use for sync triggering
                        Sends a trigger pulse when the ramp is started.
        kwargs:
            num_points [int]: Number of datapoints to use, defines smoothness. Default
                        is 1000/sec.
            trigger_width [float]: Length of sync trigger pulse in s. Default 1e-3.
            trigger_polarity [str]: Direction of sync trigger pulse.

        """

        trigger_width = kwargs.get("trigger_width", 1e-3)
        trigger_polarity = kwargs.get("trigger_polarity", "norm")
        points = kwargs.get("num_points", int(ramp_time * 1000))
        wait_time = ramp_time / points
        if wait_time < 1e-6:
            raise Exception("QDac 2 wait_time is to small (<1e-6s)")

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
            start_values = [param() for param in parameters]

        channels = [param._instrument for param in parameters]
        for channel, start, stop in zip(channels, start_values, end_values):
            dc_sweep = channel.dc_sweep(
                start_V=start, stop_V=stop, points=points, dwell_s=wait_time, backwards=(start > stop)
            )
            # There appears to be a bug with the built in dc_sweep of the QDAC!
            # The sweep direction is always from the lower to the large value if
            # backwards==False and the other way round if it is true.
            # Once this is fixed, remove the backwards argument from function call!

        if sync_trigger is not None:
            if sync_trigger in range(1, 6):
                trigger = dc_sweep.start_marker()
                qdac.external_triggers[sync_trigger - 1].width_s(trigger_width)
                qdac.external_triggers[sync_trigger - 1].polarity(trigger_polarity)
                qdac.external_triggers[sync_trigger - 1].source_from_trigger(trigger)
            else:
                logger.warning(
                    f"{sync_trigger} is no valid sync trigger for QDac II. Choose an integer between 1 and 5!"
                )

        qdac.start_all()
        qdac.free_all_triggers()

    def pulse(
        self,
        parameters: list[Parameter],
        *,
        setpoints: list[list[float]],
        delay: float,
        sync_trigger=None,
        **kwargs,
    ) -> None:
        """
        Qumada Pulse method using the QDacII dc_list to set arbitrary pulses.
            parameters: List of parameters to be set.
                        Elements have to be from the same QDACII
            setpoints:  List of setpoint arrays.
            delay:      Time in between to setpoints in s. Has to be >=1e-6 s
            sync_trigger [int|None]: Ext Trigger output (1-6) to use for sync triggering
                        Sends a trigger pulse when the ramp is started.
        kwargs:
            trigger_width [float]: Length of sync trigger pulse in s. Default 1e-3.
            trigger_polarity [str]: Direction of sync trigger pulse.

        """

        trigger_width = kwargs.get("trigger_width", 1e-3)
        trigger_polarity = kwargs.get("trigger_polarity", "norm")
        # Make sure everything is in order...
        assert len(parameters) == len(setpoints)
        for points in setpoints:
            assert len(points) == len(setpoints[0])
            for parameter in parameters:
                assert parameter._short_name == "dc_constant_V"
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception(
                "Parameters are from more than one instrument. \
                This would lead to non synchronized ramps."
            )
        qdac: QDac2 = instruments.pop()
        assert isinstance(qdac, QDac2)
        if delay < 1e-6:
            raise Exception("Delay for QDacII pulse is to small (<1 us)")
        channels = [param._instrument for param in parameters]
        self.dc_lists = [
            channel.dc_list(
                voltages=points,
                dwell_s=delay,
            )
            for channel, points in zip(channels, setpoints)
        ]

        if sync_trigger is not None:
            if sync_trigger in range(1, 6):
                trigger = self.dc_lists[0].start_marker()
                qdac.external_triggers[sync_trigger - 1].width_s(trigger_width)
                qdac.external_triggers[sync_trigger - 1].polarity(trigger_polarity)
                qdac.external_triggers[sync_trigger - 1].source_from_trigger(trigger)
            else:
                logger.warning(
                    f"{sync_trigger} is no valid sync trigger for QDac II. Choose an integer between 1 and 5!"
                )
        qdac.start_all()
        qdac.free_all_triggers()

    def setup_trigger_in():
        raise Exception(
            "QDac2 does not have a trigger input \
            not yet supported!"
        )

    def clean_generators(self):
        for dc_list in self.dc_lists:
            dc_list.abort()
        self.dc_lists = []

    @staticmethod
    def query_instrument(parameters: list[Parameter]):
        """Check if all parameters are from the same instrument"""
        instruments = {parameter.root_instrument for parameter in parameters}
        if len(instruments) > 1:
            raise Exception(
                "Parameters are from more than one instrument. \
                This would lead to non synchronized ramps."
            )
        qdac: QDac2 = instruments.pop()
        assert isinstance(qdac, QDac2)
        return qdac
