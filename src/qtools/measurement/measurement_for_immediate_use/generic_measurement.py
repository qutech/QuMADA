#!/usr/bin/env python3

import time
import qcodes as qc
from copy import deepcopy
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter

from qcodes.utils.dataset.doNd import do1d, do2d, dond, LinSweep

from qtools.measurement.measurement import MeasurementScript
#%% To be loaded from DB later on/Entered via GUI
parameters = {"topgate":{"voltage" : {"type" : "dynamic",
                                      "start": 0,
                                      "stop" : 3,
                                      "num_points" : 0.1,
                                      "delay": 0.01},
                          "current" : {"type" : "gettable"},
                          "output_enabled": {"type" : "static",
                                            "value": True},
                          "current_compliance": {"type" : "static",
                                            "value" : 1e-9}},
              "source_drain": {"amplitude": {"type": "static",
                                              "value": 1},
                                "frequency": {"type": "static",
                                              "value":173},
                                "current": {"type": "gettable"},
                                "phase": {"type" : "gettable"}},
              "left_barrier": {"voltage": {"type": "static",
                                            "value": 2}},
              "right_barrier": {"voltage": {"type": "static",
                                            "value": 2}}}

metadata = {"exp_name" : "Test",
            "sample_name" : "Testsample"}

#%%
class Generic_1D_Sweep(MeasurementScript):

    def run(self, 
            parameters: dict,
            metadata: dict) -> list():
        """
        Perform 1D sweeps for all dynamic parameters
        """
        #self.setup(parameters, metadata)
        self.initialize()
        data = list()
        time.sleep(5)
        for sweep in self.dynamic_sweeps: 
            sweep._param.set(sweep.get_setpoints)
            data.append(
                dond(sweep,
                     *tuple(self.gettable_channels)))
            self.reset()
            
        return data


#%%
class Generic_nD_Sweep(MeasurementScript):
    """
    Perform n-Dimensional sweep with n dynamic parameters.
    """
    
    def run(self,
            parameters: dict,
            metadata: dict) -> list:
        
        self.initialize()
        time.sleep(5)
        data = dond(*tuple(self.dynamic_sweeps),
                    *tuple(self.gettable_channels))
        self.reset()
        return data