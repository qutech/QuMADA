#!/usr/bin/env python3

import time

from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter

from qcodes.utils.dataset.doNd import do1d

from qtools.measurement.measurement import MeasurementScript


class InducingMeasurementScript(MeasurementScript):
    def setup(self):
        # Define gates and gate parameters
        self.gate_parameters["test"] = None
        self.gate_parameters["source_drain"] = dict.fromkeys(["amplitude",
                                                              "frequency",
                                                              "current"])
        self.gate_parameters["topgate"] = dict.fromkeys(["voltage",
                                                         "current",
                                                         "current_compliance"])
        self.gate_parameters["barrier1"] = dict.fromkeys(["voltage"])
        self.gate_parameters["barrier2"] = dict.fromkeys(["voltage"])

        self.properties = {
            "start": 0.0,
            "stop": 4.0,
            "num_points": 100,
            "delay": 0.01
        }

        load_or_create_experiment("inducing", "test")

    def run(self):
        source_drain = self.gate_parameters["source_drain"]
        topgate = self.gate_parameters["topgate"]
        barrier1 = self.gate_parameters["barrier1"]
        barrier2 = self.gate_parameters["barrier2"]
        source_drain["amplitude"].set(0.0)
        topgate["voltage"].set(0.0)
        barrier1["voltage"].set(0.0)
        barrier2["voltage"].set(0.0)

        source_drain["amplitude"].set(1.0) # Filter function in background (e.g. 10mV real voltage)
        source_drain["frequency"].set(73)

        barrier1["voltage"].ramp(2.0)
        barrier2["voltage"].ramp(2.0)

        time.sleep(5)

        # sweep up
        param_meas = (source_drain["current"], topgate["current"])
        data_up = do1d(topgate["voltage"],
                       param_meas=param_meas,
                       **self.properties)

        # Switch start and stop properties
        properties_down = self.properties
        properties_down["start"] = self.properties["stop"]
        properties_down["stop"] = self.properties["start"]
        # sweep down
        data_down = do1d(topgate["voltage"],
                         param_meas=(source_drain["current"], topgate["current"]),
                         **properties_down)