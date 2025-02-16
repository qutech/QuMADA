# Copyright (c) 2025 JARA Institute for Quantum Information
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
# - Hendrik Bluhm

from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
import threading

class DummyDacLock(DummyDac):
    """
    A DummyDAC driver with lock functionality to allow calls from several threads, thus enabling several independent parallel measurements. 
    A lock is acquired when programming a ramp and released once it is triggered.
    """
    enableLocking : bool = True

    def __init__(self, name, **kwargs):
       super().__init__(name, **kwargs)
       self.interfaceLock = threading.Lock() 
       del self.functions["force_trigger"]
       #removes result of self.add_function("force_trigger", call_cmd=self._is_triggered.set)

    def force_trigger(self): 
        self._is_triggered.set
        if self.enableLocking: self.interfaceLock.release()

    def ramp(self, channel, start, stop, duration, num_points):
        if self.enableLocking: self.interfaceLock.acquire()
        super().ramp(channel, start, stop, duration, num_points)