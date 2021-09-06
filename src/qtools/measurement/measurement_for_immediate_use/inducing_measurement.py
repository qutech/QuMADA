#!/usr/bin/env python3

"""Inducing Measurement Script"""

import time

from copy import deepcopy

from qcodes.dataset.experiment_container import load_or_create_experiment

from qcodes.utils.dataset.doNd import do1d

from qtools.measurement.measurement import MeasurementScript


class InducingMeasurementScript(MeasurementScript):
    """Inducing measurement"""
    def setup(self):
        """Setup gates, measurement properties and load/create qcodes experiment."""
        # Define gates and gate parameters
        self.add_gate_parameter("amplitude", "source_drain")
        self.add_gate_parameter("frequency", "source_drain")
        self.add_gate_parameter("current", "source_drain")
        self.add_gate_parameter("voltage", "topgate")
        self.add_gate_parameter("current", "topgate")
        self.add_gate_parameter("output_enabled", "topgate")
        self.add_gate_parameter("current_compliance", "topgate")
        self.add_gate_parameter("voltage", "barrier1")
        self.add_gate_parameter("voltage", "barrier2")

        self.properties = {
            "start": 0.0,
            "stop": 4.0,
            "num_points": 100,
            "delay": 0.01
        }

        load_or_create_experiment("inducing", "test")

    def run(self):
        """Run the measurement."""
        source_drain = self.gate_parameters["source_drain"]
        topgate = self.gate_parameters["topgate"]
        barrier1 = self.gate_parameters["barrier1"]
        barrier2 = self.gate_parameters["barrier2"]
        source_drain["amplitude"].set(0.004)
        topgate["output_enabled"].set(True)
        topgate["voltage"].set(0.0)
        barrier1["voltage"].set(0.0)
        barrier2["voltage"].set(0.0)

        source_drain["amplitude"].set(1.0)  # Filter function in background (e.g. 10mV real voltage)
        source_drain["frequency"].set(73)

        barrier1["voltage"].set(2.0)
        barrier2["voltage"].set(2.0)

        time.sleep(5)

        # sweep up
        # param_meas = (source_drain["current"], topgate["current"])
        do1d(topgate["voltage"],
             self.properties["start"],
             self.properties["stop"],
             self.properties["num_points"],
             self.properties["delay"],
             source_drain["current"],
             topgate["current"])

        # Switch start and stop properties
        properties_down = deepcopy(self.properties)
        properties_down["start"] = self.properties["stop"]
        properties_down["stop"] = self.properties["start"]
        # sweep down
        do1d(topgate["voltage"],
             properties_down["start"],
             properties_down["stop"],
             properties_down["num_points"],
             properties_down["delay"],
             source_drain["current"],
             topgate["current"])
