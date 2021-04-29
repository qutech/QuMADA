# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 15:54:01 2021

@author: till3
"""

#File for testing with dummy instruments/dummy station

#%%
import time
import qcodes as qc
#from qtools.instrument_drivers.Harvard.FZJ_Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
# from qcodes.instrument_drivers.ZI.ZIMFLI0 import ZIMFLI
import qcodes.instrument_drivers.Lakeshore.Model_325 as ls #Temperature sensor
import os
#Magnet Power Supply missing here
from qcodes.tests.instrument_mocks import DummyInstrument

from qcodes.plots.pyqtgraph import QtPlot
from qcodes.instrument.parameter import ManualParameter
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers

from qcodes.plots.qcmatplotlib import MatPlot
#%%

qc.Instrument.close_all()

#%%
#%% Add dummy/virtual instruments here
t0=time.time()
def experiment_time(t0=t0):
      t= round((time.time()-t0),4)
      return t


clock = DummyInstrument (name="clock")#'runtime', gates=['clock1'])
clock.add_parameter('time', unit = 's', get_cmd= experiment_time)


#Add the clock to the station- it now works like a "real" instrument
#station.add_component(clock)

#Define a counter, that can be used in combination with the "sweep" function 
#later in order to define the measurement loops
counter=DummyInstrument(name="dummy2")
counter.add_parameter('count', set_cmd=None)

#%% Add instruments to the station


station=qc.Station(clock, counter)#, keithley2)

print('station is now set up with the following instruments:\n %s',
      station.components)



