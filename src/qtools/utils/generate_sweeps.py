# -*- coding: utf-8 -*-
"""
Created on Thu Jan 27 16:27:19 2022

@author: lab
"""

import numpy as np

def generate_sweep(start, stop, num_points, include_backward = False):
    """
    Creates a linear array with equally spaced setpoints ranging from start to stop.
    If include_backwars is set True, the array will contain twice as much 
    setpoints going from start to stop and back down to start again.
    """
    if include_backward:
        sweep = np.array((*np.linspace(start, stop, num_points), *np.linspace(stop, start, num_points)))
    else: 
        sweep = np.linspace(start, stop, num_points)
    return sweep

def replace_parameter_settings(parameters: dict,
                               old_val : str,
                               new_value):
    """
    Replaces parameters based on their values with other value. Can be used to 
    pass setpoint arrays to parameter-dicts created from json files without 
    having to change the values by hand everytime.
    """
    for gate, param in parameters.items():
        for x,y in param.items():
            for name, val in y.items():
                if val == old_val:
                    parameters[gate][x][name]=new_value                    
    return parameters
    