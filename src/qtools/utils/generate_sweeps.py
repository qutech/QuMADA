"""
Created on Thu Jan 27 16:27:19 2022

@author: lab
"""

import numpy as np


def generate_sweep(start, stop, num_points, backsweep=False):
    """
    Creates a linear array with equally spaced setpoints ranging from start to stop.
    If include_backwars is set True, the array will contain twice as much
    setpoints going from start to stop and back down to start again.
    """
    if backsweep:
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
                    parameters[gate][x][name] = new_value
    return parameters


import copy


def update_parameter_settings(parameters: dict,
                               old_val : str,
                               new_value):
    """
    Replaces parameters based on their values with other value. Can be used to
    pass setpoint arrays to parameter-dicts created from json files without
    having to change the values by hand everytime.
    Does not modify the original dict, but return a modified deep copy.
    """
    updated_parameters = copy.deepcopy(parameters)
    for gate, param in updated_parameters.items():
        for x,y in param.items():
            for name, val in y.items():
                if val == old_val:
                    updated_parameters[gate][x][name] = new_value
    return updated_parameters

def parse_code_from_json(parameters):
    '''executes simple chunks of python code in strings starting with _'''
    updated_parameters = copy.deepcopy(parameters)
    for gate, param in updated_parameters.items():
        for x,y in param.items():
            for name, val in y.items():
                if isinstance(val, str):
                    if val[0] == "_":
                        updated_parameters[gate][x][name] = eval(val[1:])
                        print(val)
    return updated_parameters
