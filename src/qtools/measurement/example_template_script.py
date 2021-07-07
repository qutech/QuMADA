#!/usr/bin/env python3
"""
Example template measurement script
"""

from typing import Any, Dict, Sequence

from qcodes.instrument import Parameter, channel
from qcodes.utils.dataset.doNd import do1d

from qtools.measurement.measurement import VirtualGate
from qtools.data.measurement import FunctionType as ft

# TODO: Abstract MeasurementScript Class

class MeasurementScript():
    def __init__(self):
        self.properties: Dict[Any, Any] = {}
        self.channels: Dict[Any, Parameter] = {}

    def setup(self):
        """
        Setup your channels here.
        """
        # Set Measurement properties
        self.properties = {
            "sample_name": "s20210434",
            "device_name": "d01",
            "volt_start": 0,
            "volt_end": 2,
            "volt_step": .1,
            "volt_delay": .05,
            "repetitions": 1,
            "backsweep": True,
            "source_drain": {
                "frequency": 173,
                "amplitude": 1,
                "voltage_divider": 1e-4,
                "sensitivity": "",
                "reserve": "",
                "time_constant": 1e-3
            },
            "topgate": {
                "current_range": "auto",
            },
            "barriers": {
                "voltage": 2,
                "wait": 2
            },
            "safety_limit_leakage": 1e-8,
            "safety_limit_curr": 1e-6
        }

        # define empty channels, that have to be mapped later
        self.channels = dict.fromkeys(["sd_amplitude",
                                       "sd_frequency",
                                       "sd_current",
                                       "sd_output_enable",
                                       "tg_voltage",
                                       "tg_current",
                                       "b1_voltage",
                                       "b2_voltage"])

    def run(self):
        """
        Run the measurements.
        """
        # Sort channels
        def channels_by_keys(keys: Sequence, prefix="", suffix="") -> Dict[Any, Parameter]:
            """
            Filters self.channels by the given keys and returns a separate dictionary.
            It is possible to remove prefixes or suffixes from the original keys.

            Args:
                keys (Sequence): List of the desired entries from self.channels
                prefix (str, optional): prefix that shall be removed from the keys. Defaults to "".
                suffix (str, optional): suffix that shall be removed from the keys. Defaults to "".

            Returns:
                dict[Any, Parameter]: Dictionary with the matched channels.
            """
            return {x.removeprefix(prefix).removesuffix(suffix): self.channels[x] for x in keys}

        source_drain = channels_by_keys(["sd_amplitude", "sd_frequency", "sd_current", "sd_output_enable"], prefix="sd_")
        topgate = channels_by_keys(["tg_voltage", "tg_current"], prefix="tg_")
        barriers = [channels_by_keys([f"b{i}_voltage"], prefix=f"b{i}_") for i in range(2)]

        volt_start = float(self.properties["volt_start"])
        volt_end = float(self.properties["volt_end"])
        volt_step = float(self.properties["volt_step"])
        volt_delay = float(self.properties["volt_delay"])
        num_points = int((volt_end - volt_start)/volt_step)

        repetitions = self.properties["repetitions"]

        for i in range(repetitions):
            data_up = do1d(topgate["voltage"], volt_start, volt_end, num_points,
                           volt_delay, source_drain["current"])
            print(data_up)

            data_down = do1d(topgate["voltage"], volt_end, volt_start, num_points,
                             volt_delay, source_drain["current"])
            print(data_down)
