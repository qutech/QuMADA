# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 18:38:47 2020

@author: Huckemann
"""
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 13:38:42 2020

@author: Huckemann
"""
#%% Imports should be moved to main script
import time
import qcodes as qc
import os
#Magnet Power Supply missing here
from qcodes.tests.instrument_mocks import DummyInstrument

from qcodes.plots.pyqtgraph import QtPlot
from qcodes.instrument.parameter import ManualParameter
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers

from qcodes.plots.qcmatplotlib import MatPlot
import qcodes.loops
import numpy as np

#%%
from . import get_from_station as gfs
#%%


class input_mapping():
    '''
    Mapping of "physical" sample gates to device channels.
    Requires user input.
    To Do:
        - Version without user input
        - Loading/Saving
        - Measurement device types
        - Think about dictionary structure
        - 
    '''
    def __init__(self, station):
        self.station = station
        self.gate_number = int(input("Please enter number of gates: "))
        self.gates = {} #Mapping gate name <=> list with device channels: [0]=voltage, [1]=current
        self.gate_types= self._load_gate_types()
        self.add_gates()
    
    def _load_gate_types(self, file = "./gate_types.dat"):
        '''
        Loads list of valid gate types from file. 
        Todo: - Handle exceptions
              - Validate files
              - Allow for user input/saving      
        '''
        types = set()
        f = open(file, 'r')
        for line in f:
            if line[0] != "#" : types.add(line.rstrip('\n'))
        f.close()
        return types
                
    def add_gates(self):
        '''
        Guides user through the specification of the used gates at startup.
        '''
        for i in range(self.gate_number):
            self.add_gate()             
    
    def remove_gate(self, gate = None):
        '''
        Allows user to delete gates.
        ToDo: Show list of available entries
        '''
        if gate == None:
            gate = input("Enter name of gate you want to delete: \n")
        try:
            del self.gates[gate]
        except KeyError:
            print("This gate does not exist")
            
    def add_gate(self):
        '''
        Method that should be used for adding gates to the mapping. Requires
        user input.
        '''
        key = input("Please enter gate name: ")
        gate_type = self._gate_type_validator(self.gate_types)
        volt_channel = self._add_volt()
        current_channel = self._add_current()
        self.gates[key] = {}
        self.gates[key]["gate_type"] = gate_type 
        self.gates[key]["volt"] = volt_channel
        self.gates[key]["current"] = current_channel
                               
    def _add_current(self):
        '''
        Add current channel to gate entry
        '''
        string = "Please select a channel to apply and measure currents for this gate.\n"
        string += 'You can skip this by typing "exit"'
        current_channel = gfs.select_channel(self.station, 
                                          information = string)                    
        return current_channel
    def _add_volt(self):
        '''
        Add volt channel to gate entry
        '''
        string = "Please select a channel to apply and measure voltages for this gate.\n"
        volt_channel = gfs.select_channel(self.station, 
                                          information = string)                    
        return volt_channel
    def _gate_type_validator(self, gate_types, gate_type = None):
        '''
        Checks whether chosen gate type is valid. Necessary to rely on gate_type
        variable in the measurement script.
        '''
        if gate_type in gate_types:
            return gate_type
        elif gate_type == None:
            gate_type = input("Please enter gate type: \n")
            return self._gate_type_validator(gate_types, gate_type)
        else:
            print("Invalid gate type. Known gate types are \n" + str(gate_types))
            print("You can use 'other' for unspecified gates. Support for adding new types will be added later")
            return self._gate_type_validator(gate_types)
    