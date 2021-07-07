#!/usr/bin/env python3

import time

from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter

from qcodes.utils.dataset.doNd import do1d

from qtools.measurement.measurement import MeasurementScript


class InducingMeasurementScript(MeasurementScript):
    def __init__(self):
        super().__init__()

    def setup(self):
        self.gate_parameters = dict.fromkeys(["sd_amplitude",
                                              "sd_frequency",
                                              "sd_current",
                                              "tg_voltage",
                                              "tg_current",
                                              "tg_current_compliance",
                                              "b1_voltage",
                                              "b2_voltage"])

        self.properties = {
            "start": 0.0,
            "stop": 4.0,
            "num_points": 100,
            "delay": 0.01
        }

        load_or_create_experiment("inducing", "test")

    def run(self):
        channels = self.channels
        channels["sd_amplitude"].set(0.0)
        channels["tg_voltage"].set(0.0)
        channels["b1_voltage"].set(0.0)
        channels["b2_voltage"].set(0.0)

        channels["sd_amplitude"].set(1.0) # Filter function in background (e.g. 10mV real voltage)
        channels["sd_frequency"].set(73)

        channels["b1_voltage"].ramp(2.0)
        channels["b2_voltage"].ramp(2.0)

        time.sleep(5)

        # sweep up
        param_meas = (channels["sd_current"], channels["tg_current"])
        data_up = do1d(channels["tg_voltage"],
                       param_meas=param_meas,
                       **self.properties)

        # Switch start and stop properties
        properties_down = self.properties
        properties_down["start"] = self.properties["stop"]
        properties_down["stop"] = self.properties["start"]
        # sweep down
        data_down = do1d(channels["tg_voltage"],
                         param_meas=(channels["sd_current"], channels["tg_current"]),
                         **properties_down)