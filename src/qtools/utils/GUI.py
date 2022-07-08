# -*- coding: utf-8 -*-
"""
Created on Fri May 20 12:41:08 2022

@author: Till
"""

import sys

from subprocess import Popen

from qcodes.monitor.monitor import  Monitor
from qtools.instrument.mapping.base import filter_flatten_parameters
from qtools.measurement.measurement import MeasurementScript
from qcodes.station import Station        

def open_web_gui(parameters):
    """
    Opens Gui from qcodes.monitor.monitor
    parameters: Provides the parameters to display. Has to be Station object, 
    Qtools MeasurementScript object or list of qcodes parameters.
    When a station object is used, all parameters of all components are shown.
    """
    if isinstance(parameters, Station):
        params = [val for val in filter_flatten_parameters(parameters.components).values()]
    elif isinstance(parameters, MeasurementScript):
        params = []
        try:
            channels = [val for val in parameters.gate_parameters.values()]
        except:
            print("Error not yet implemented. Maybe you forgot to do the mapping first?")
            return False
        for gate in channels:
            for item in gate.values():
                params.append(item)
    elif isinstance(parameters, list):
        params = parameters
    else: 
        print("The provided parameters are invalid. Please pass as Station \
              object, a Measurement Script (after parameter mapping) or a \
              list of parameters")
        return False
    monitor_process = Popen([sys.executable, "-m", "qcodes.monitor.monitor"], shell = True)
    monitor = Monitor(*params)
    return monitor, monitor_process

        
        
        
    
    