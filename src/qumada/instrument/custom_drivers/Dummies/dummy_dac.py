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
# - Till Huckeman


# most of the drivers only need a couple of these... moved all up here for clarity below
from __future__ import annotations

import threading
from time import sleep

import numpy as np
from qcodes.instrument import ChannelList, Instrument, InstrumentChannel
from qcodes.validators import validators as vals


# %%
class DummyDac_Channel(InstrumentChannel):
    def __init__(self, parent, name, channel):
        super().__init__(parent, name)
        self._channel = channel

        self.add_parameter("voltage", unit="V", set_cmd=None, vals=vals.Numbers(-10, 10))
        self.voltage.set(0)

    def ramp(self, start, stop, duration, num_points):
        self.parent.ramp(self, start, stop, duration, num_points)


class DummyDac(Instrument):
    def __init__(self, name, trigger_event=threading.Event(), **kwargs):
        super().__init__(name, **kwargs)
        channels = ChannelList(self, "Instrument_Channels", DummyDac_Channel)
        self._is_triggered = trigger_event

        for i in range(1, 5):
            channel = DummyDac_Channel(self, f"ch{i:02}", i)
            channels.append(channel)
            self.add_submodule(f"ch{i:02}", channel)
        # self.add_parameter("voltage", unit="V", set_cmd=None, vals=vals.Numbers(-10, 10))
        # self.voltage.set(0)
        self.add_submodule("channels", channels.to_channel_tuple())
        self.add_function("force_trigger", call_cmd=self._is_triggered.set)

    def _run_ramp(self, channel, start, stop, duration, num_points):
        for setpoint in np.linspace(start, stop, int(num_points)):
            channel.voltage(setpoint)
            sleep(duration / num_points)

    def ramp(self, channel, start, stop, duration, num_points):
        self.thread = threading.Thread(
            target=self._run_ramp,
            args=(channel, start, stop, duration, num_points),
            daemon=True,
        )
        self.thread.start()

    def ramp_channels(self, channels: list, start_values: list, stop_values: list, duration, num_points):
        self.thread = threading.Thread(
            target=self._run_ramp_channels,
            args=(channels, start_values, stop_values, duration, num_points),
            daemon=True,
        )
        self.thread.start()

    def _run_ramp_channels(self, channels: list, start_values: list, stop_values: list, duration, num_points):
        setpoints = []
        for ch, start, stop in zip(channels, start_values, stop_values):
            setpoints.append(np.linspace(start, stop, num_points))
        setpoints_inv = []
        for i in range(num_points):
            setpoints_inv.append([setpoints[j][i] for j in range(len(channels))])
        for setpoint in setpoints_inv:
            for i in range(len(channels)):
                channels[i].voltage(setpoint[i])
            sleep(duration / num_points)

    def _run_triggered_ramp(self, channel, start, stop, duration, stepsize=0.01):
        _ = self._is_triggered.wait()
        num_points = int((stop - start) / stepsize)
        for setpoint in np.linspace(start, stop, num_points):
            channel.voltage(setpoint)
            sleep(duration / num_points)

    def _run_triggered_ramp_channels(self, channels, start_values, stop_values, duration, num_points):
        setpoints = []
        for start, stop in zip(start_values, stop_values):
            setpoints.append(np.linspace(start, stop, int(num_points)))
        setpoints_inv = []
        for i in range(int(num_points)):
            setpoints_inv.append([setpoints[j][i] for j in range(len(channels))])
        _ = self._is_triggered.wait()
        for setpoint in setpoints_inv:
            for i in range(len(channels)):
                channels[i].voltage(setpoint[i])
            sleep(duration / num_points)

    def _run_triggered_pulse_channels(self, channels, setpoints, duration):
        setpoints_inv = []
        num_points = len(setpoints[0])
        for i in range(int(len(setpoints[0]))):
            setpoints_inv.append([setpoints[j][i] for j in range(len(channels))])
        _ = self._is_triggered.wait()
        for setpoint in setpoints_inv:
            for i in range(len(channels)):
                channels[i].voltage(setpoint[i])
            sleep(duration / num_points)

    def _triggered_ramp(self, channel, start, stop, duration, num_points):
        self.thread = threading.Thread(
            target=self._run_triggered_ramp,
            args=(channel, start, stop, duration, num_points),
            daemon=True,
        )
        self.thread.start()

    def _triggered_ramp_channels(self, channels, start_values, stop_values, duration, num_points):
        self.thread = threading.Thread(
            target=self._run_triggered_ramp_channels,
            args=(channels, start_values, stop_values, duration, num_points),
            daemon=True,
        )
        self.thread.start()

    def _triggered_pulse_channels(self, channels, setpoints, duration):
        self.thread = threading.Thread(
            target=self._run_triggered_pulse_channels,
            args=(channels, setpoints, duration),
            daemon=True,
        )
        self.thread.start()


# %%
