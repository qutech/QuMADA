"""
Created on Mon Jan  2 17:21:37 2023

@author: till3
"""
import ctypes  # only for DLL-based instrument
import random

# most of the drivers only need a couple of these... moved all up here for clarity below
from time import sleep, time

import numpy as np
import qcodes as qc
from qcodes.instrument import (
    Instrument,
    InstrumentChannel,
    InstrumentModule,
    ManualParameter,
    MultiParameter,
    Parameter,
    VisaInstrument,
)
from qcodes.utils import validators as vals
from qcodes.validators import Arrays, ComplexNumbers, Enum, Ints, Numbers, Strings


#%%
class dmm_results(Parameter):
    def get_raw(self):
        return np.random.rand(1)[0]


class dmm_buffer(Parameter):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.buffer_data = []
        self.buffer_length = None
        self.SR = None
        self.is_finished = True

    def ready_buffer(self):
        self.SR = self.root_instrument.buffer_SR()
        self.buffer_length = self.root_instrument.buffer_n_points()
        self.is_finished = False

    def start(self):
        if self.is_finished:
            raise Exception("Buffer is not ready!")
        for i in range(0, self.buffer_length):
            self.buffer_data.append(np.random.sample())
            sleep(1 / self.SR)
        self.is_finished = True

    def reset(self):
        self.buffer_data = []

    def get_raw(self):
        return self.buffer_data


class DummyDmm(Instrument):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        self.add_parameter(
            "voltage",
            unit="V",
            parameter_class=dmm_results,
        )

        self.add_parameter("buffer", unit="V", parameter_class=dmm_buffer)

        self.add_parameter(
            "buffer_SR",
            set_cmd=None,
            vals=Ints(0, 512),
        )

        self.add_parameter(
            "trigger_mode",
        )

        self.add_parameter(
            "buffer_n_points",
            set_cmd=None,
        )

        self.add_function("start", call_cmd=self.start_buffer)

    def start_buffer(self):
        print("Started buffer")
        self.buffer.start()
        return None

    def ready_buffer(self):
        print("Buffer is now ready")
        self.buffer.ready_buffer()
        return None

    def reset_buffer(self):
        print("Buffer was resetted")
        return None
