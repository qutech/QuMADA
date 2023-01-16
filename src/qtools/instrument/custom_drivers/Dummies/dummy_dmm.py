# -*- coding: utf-8 -*-
"""
Created on Mon Jan  2 17:21:37 2023

@author: till3
"""
# most of the drivers only need a couple of these... moved all up here for clarity below
from time import sleep
import numpy as np

from qcodes.instrument import (
    Instrument,
    Parameter,
)
import threading
from qcodes.utils import validators as vals

#%%
class dmm_results_random(Parameter):
    
    def get_raw(self):
        return np.random.sample()
    
class dmm_results_sinus(Parameter):
    
    def get_raw(self):
        length = self.root_instrument.buffer_n_points()
        if length and length>0:
            return [np.sin(2*np.pi*x/(self.root_instrument.buffer_n_points()**2/self.root_instrument.buffer_SR())) for x in np.linspace(0, length, length)]
        else: 
            raise Exception("Set buffer_n_points first to a positive value")
    
class dmm_buffer(Parameter):
    
    def __init__(self, name,**kwargs):
        super().__init__(name, **kwargs)
        self.buffer_data = []
        self.buffer_length = 512
        self.SR = 512
        self.is_finished = True
        self.subscribed_params =  list()
        self.triggered: bool = False
        self._is_triggered = self.root_instrument._trigger_event
                
    def subscribe(self, param):
        assert param.root_instrument == self.root_instrument
        if param not in self.subscribed_params:
            self.subscribed_params.append(param)
           
    def ready_buffer(self):
        self.SR = self.root_instrument.buffer_SR()
        self.buffer_length = self.root_instrument.buffer_n_points()
        self.buffer_data = [list() for _ in self.subscribed_params]
        self.is_finished = False
        
    def start(self):
        if self.is_finished:
            raise Exception("Buffer is not ready!")
        self.thread = threading.Thread(target=self._run, args=(), daemon = True)
        self.thread.start()
        
        
    def _run(self):
        _is_triggered = self._is_triggered.wait()
        for i in range(0, self.buffer_length):
            for j in range(len(self.subscribed_params)):
                datapoint = self.subscribed_params[j]()
                if type(datapoint) == float:
                    self.buffer_data[j].append(self.subscribed_params[j]())
                elif type(datapoint) == list:
                    self.buffer_data[j].append(self.subscribed_params[j]()[i])
            sleep(1/self.SR) 
        self.is_finished = True
            
    def reset(self):
        self.buffer_data = []
            
    def get_raw(self):
        return self.buffer_data

class DummyDmm(Instrument): 
    
    def __init__(self, name, trigger_event = threading.Event(), **kwargs):
        super().__init__(name, **kwargs)
        
        self._trigger_event = trigger_event
        
        self.add_parameter(
            "voltage", 
            unit = "V",
            parameter_class = dmm_results_sinus,
            )
        
        self.add_parameter(
            "current",
            unit = "A",
            parameter_class = dmm_results_random)
        
        self.add_parameter(
            "buffer",
            unit = "V",
            parameter_class = dmm_buffer)
        
        self.add_parameter(
            "buffer_SR",
            unit = "Sa/s",
            set_cmd = None,
            vals = Ints(0, 512),
             )
        
        self.add_parameter(
            "trigger_mode",
            )
        
        self.add_parameter(
            "is_finished",
            get_cmd = self._is_finished)
        
        self.add_parameter(
            "buffer_n_points",
            set_cmd = None,
            vals = Ints(0,16383)
            )
        
        self.add_parameter(
            "triggered",
            set_cmd = None,
            vals = vals.Bool())
        self.triggered(False)
        
        self.add_function(
            "start",
            call_cmd = self._start_buffer)
        
        self.add_function(
            "ready_buffer",
            call_cmd = self._ready_buffer)
        
        self.add_function(
            "reset_buffer",
            call_cmd = self._reset_buffer)
        
    def _force_trigger(self):
        self.buffer._is_triggered.set()
        return None
                
    def _start_buffer(self):
        print("Started buffer")
        self.buffer.start()
        return None
    
    def _ready_buffer(self):
        print("Buffer is now ready")
        self.buffer.ready_buffer()
        self.buffer._is_triggered = self._trigger_event
        return None
    
    def _reset_buffer(self):
        print("Buffer was resetted")
        self.buffer.buffer_data = []
        return None
    
    def _is_finished(self):
        return self.buffer.is_finished