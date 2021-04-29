# -*- coding: utf-8 -*-
import initialize
from qcodes import ManualParameter, ScaledParameter
from qcodes.utils.dataset.doNd import do1d, do2d, plot

def inducing_measurement(source_drain, topgate, barriers, volt_start, volt_end,
                         volt_step, volt_delay, sample_name, device_name, 
                         repetitions = 1, backsweep = True, sd_frequency = 173,
                         sd_amplitude = 1, sd_voltage_divider = 1e-4, 
                         sd_sensitivity = "", sd_reserve = "",
                         sd_time_constant = 1e-3, topgate_current_range ="auto",
                         safety_limit_leakage= 1e-8, safety_limit_curr = 1e-6,
                         barriers_voltage = 2, barriers_wait = 10,
                         ):
    
    """
    First sketch of what an inducing measurement would look like that only
    depends on gates rather than on instruments.
    Requires:
    Station, gate_mapping, 

    """
    
    #Set everything to the correct values (there should be some func to do this)
    initialize(source_drain.volt, function = "voltage_source", **kwargs)
    initialize(source_drain.current, function = "current_sense", **kwargs)
    initialize(topgate.volt, function = "voltage_source", **kwargs)
    if topgate.current != None:
        initialize(topgate.current, function = "current_sense", **kwargs)
    for barrier in barriers:
        initialize(barrier.volt, function = "voltage_source", **kwargs)
        if barrier.current != None:
            initialize(barrier.current, function = "current_sense", **kwargs)
            
    source_drain_divided = ScaledParameter(source_drain.volt, 
                                           division = sd_voltage_divider)


    num_points = int((volt_end-volt_start)/volt_step)
    for i in range(0, repetitions):
        data_up = do1d(topgate.volt, volt_start, volt_end, num_points, 
                      volt_delay, source_drain.current)
                       
        data_down = do1d(topgate_volt, volt_end, volt_start, num_points,
                         voltage_delay, source_drain.current)
        
    