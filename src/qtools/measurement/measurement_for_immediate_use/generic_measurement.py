#!/usr/bin/env python3

import time
import qcodes as qc
from copy import deepcopy
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter

from qcodes.utils.dataset.doNd import do1d, do2d

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
        Runs the measurement
        """
        self.setup(parameters, metadata)
        self.initialize()
        data = list()
        time.sleep(5)
        for param in self.dynamic_parameters:
            active_param = self.properties[param["gate"]][param["parameter"]]
            channel = self.gate_parameters[param["gate"]][param["parameter"]]
            sweep_params = (channel,
                            active_param["start"],
                            active_param["stop"],
                            active_param["num_points"],
                            active_param["delay"])
            channel.set(active_param["start"])
            data.append(
                do1d(*sweep_params,
                     *tuple(self.gettable_parameters)))
            self.reset()
            
        return data

#%%
class Generic_2D_Sweep(MeasurementScript):
    
    def run(self,
            parameters: dict,
            metadata: dict):
        """
        Runs the measurement
        """
        self.setup(parameters)
        self.initialize()
        if len(self.dynamic_parameters) != 2:
            raise ValueError("parameters has to contain exactly two dynamic parameters in order to perform this measurement.")
        time.sleep(5)
        active_param1 = self.properties[self.dynamic_parameters[0]["gate"]][self.dynamic_parameters[0]["parameter"]]
        active_param2 = self.properties[self.dynamic_parameters[1]["gate"]][self.dynamic_parameters[1]["parameter"]]
        channel1 = self.gate_parameters[self.dynamic_parameters[0]["gate"]][self.dynamic_parameters[0]["parameter"]]
        channel2 = self.gate_parameters[self.dynamic_parameters[1]["gate"]][self.dynamic_parameters[1]["parameter"]]
        sweep_params=(channel1,
                     active_param1["start"],
                     active_param1["stop"],
                     active_param1["num_points"],
                     active_param1["delay"],
                     channel2,
                     active_param2["start"],
                     active_param2["stop"],
                     active_param2["num_points"],
                     active_param2["delay"])
        data = do2d(*sweep_params,
                    *tuple(self.gettable_parameters))
        self.reset()
        return data