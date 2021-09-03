#!/usr/bin/env python3

import time

from copy import deepcopy

from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter

from qcodes.utils.dataset.doNd import do1d

from qtools.measurement.measurement import MeasurementScript
#%% To be loaded from DB later on/Entered via GUI
# parameters = {"topgate":{"voltage" : {"type" : "sweepable",
#                                       "start": 0,
#                                       "stop" : 3,
#                                       "num_points" : 0.1,
#                                       "delay": 0.01},
#                           "current" : {"type" : "gettable"},
#                           "output_enabled": {"type" : "static",
#                                             "value": True},
#                           "current_compliance": {"type" : "static",
#                                             "value" : 1e-9}},
#               "source_drain": {"amplitude": {"type": "static",
#                                               "value": 1},
#                                 "frequency": {"type": "static",
#                                               "value":173},
#                                 "current": {"type": "gettable"},
#                                 "phase": {"type" : "gettable"}},
#               "left_barrier": {"voltage": {"type": "static",
#                                             "value": 2}},
#               "right_barrier": {"voltage": {"type": "static",
#                                             "value": 2}}}

# metadata = {"exp_name" : "Test",
#             "sample_name" : "Testsample"}

#%%
class Generic_1D_Sweep(MeasurementScript):
    def setup(self, parameters, metadata):
        self.metadata = metadata
        for gate, vals in parameters.items():
            self.properties[gate] = vals
            for parameter, properties in vals.items():
                self.add_gate_parameter(parameter, gate)

        load_or_create_experiment(metadata["exp_name"], metadata["sample_name"])
    def initialize(self):
        """
        Sets all static/sweepable parameters to their value/start value.
        If parameters are both, static and sweepable, they will be set to the "value" property
        and not to the "start" property.
        ToDo:
        -Is there a more elegant way than to use ".find"? Integrate "type"
        into the gate_parameter class?
        -Add as method to Measurement_script class?
        """
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("static") >= 0:
                    channel.set(self.properties[gate][parameter]["value"])
                elif self.properties[gate][parameter]["type"].find("sweepable") >= 0:
                    channel.set(self.properties[gate][parameter]["start"])

    def run(self):
        """
        Runs the measurement
        """
        get_params = list()
        data = list()
        #Create tuple with gettable parameters (Add method to do this?)
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"].find("gettable") >= 0:
                    get_params.append(channel)
        time.sleep(5)
        for gate, parameters in self.gate_parameters.items():
            for parameter, channel in parameters.items():
                if self.properties[gate][parameter]["type"] == "sweepable":
                    active_param = self.properties[gate][parameter]
                    sweep_params = (channel,
                                    active_param["start"],
                                    active_param["stop"],
                                    active_param["num_points"],
                                    active_param["delay"])
                    self.initialize()
                    data.append(
                        do1d(*sweep_params,
                             *tuple(get_params)))
        return data
