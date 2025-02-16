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

# This file is untested. See also Dummies/dummy_dacLock.py for an implementation 
# that can be tested without hardware.

from qumada.instrument.custom_drivers.Harvard.Decadac import Decadac, DacChannel
import threading

class DacChannelLock(DacChannel):
    """
    Modified DacChannel class to supprt locking.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        del self.functions["script_ramp"]
    
        # The script_ramp function added by __init__ needs to replaced to use new worker method.
        # It is simply deleted and directly defined anew. (QCoDeS Docu recommends not using functions)


    def script_ramp(self, start, end, duration, trigger=0):
       
       # make lock conditional on trigger setting (not immediate)?
       if self.root_instrument.enableLocking: 
            self.root_instrument.interfaceLock.acquire()
       super()._script_ramp(start, end, duration, trigger)

class DecadacLock(Decadac):
    """
    A DECADAC driver with lock functionality to allow calls from several threads, thus enabling several independent parallel measurements. 
    A lock is acquired when programming a ramp and released once it is triggered.
    """

    DAC_CHANNEL_CLASS = DacChannelLock
    enableLocking : bool = True 
    # flag to control whether locks are executed. May be useful if switching modes without recreating DecadacLock object, 
    # e.g. for standalone measurements or debugging.

    def __init__(self, **kwargs):
       super().__init__(**kwargs)
       self.interfaceLock = threading.Lock() # lock object associated with instrument 

    def trigger(self, trigger_setting: str):
        super().trigger(trigger_setting)
        if self.enableLocking: 
            self.interfaceLock.release()




       