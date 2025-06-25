# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Sionludi Lab


import copy

import numpy as np
from qumada.utils.load_from_sqlite_db import separate_up_down


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


def replace_parameter_settings(parameters: dict, old_val: str, new_value):
    """
    Replaces parameters based on their values with other value. Can be used to
    pass setpoint arrays to parameter-dicts created from json files without
    having to change the values by hand everytime.
    """
    for gate, param in parameters.items():
        for x, y in param.items():
            for name, val in y.items():
                if val == old_val:
                    parameters[gate][x][name] = new_value
    return parameters


def update_parameter_settings(parameters: dict, old_val: str, new_value):
    """
    Replaces parameters based on their values with other value. Can be used to
    pass setpoint arrays to parameter-dicts created from json files without
    having to change the values by hand everytime.
    Does not modify the original dict, but return a modified deep copy.
    """
    updated_parameters = copy.deepcopy(parameters)
    for gate, param in updated_parameters.items():
        for x, y in param.items():
            for name, val in y.items():
                if val == old_val:
                    updated_parameters[gate][x][name] = new_value
    return updated_parameters


def parse_code_from_json(parameters):
    """executes simple chunks of python code in strings starting with _"""
    updated_parameters = copy.deepcopy(parameters)
    for gate, param in updated_parameters.items():
        for x, y in param.items():
            for name, val in y.items():
                if isinstance(val, str):
                    if val[0] == "_":
                        updated_parameters[gate][x][name] = eval(val[1:])
                        print(val)
    return updated_parameters

def split_into_segments(setpoints, max_difference, segment_on_direction_change=True):
    """
    Used to split an array (mostly setpoints for sweeps) into multiple parts.
    No segment contains differencens in the values of its setpoints that are
    larger than max_difference. If segment_on_direction_change is True,
    a separation at each change of monotony of the setpoints is enforced. This 
    can help to separate ramps in different directions.
    
    

    Parameters
    ----------
    setpoints : Array|List of floats
        Setpoints to separate.
    max_difference : Float
        Maximum difference of setpoints in on segment.
    segment_on_direction_change : Bool, optional
        Whether a new segment should be enforced whenever the "direction"
        of the setpoints changes. The default is True.

    Returns
    -------
    segmented_setpoints : List[List[Floats]]
        Resulting segmented setpoints.

    """
    segmented_setpoints = []
    if max_difference is None:
        max_difference = np.inf
    if segment_on_direction_change is True:
        setpoints = separate_up_down(setpoints)[0]
    else:
        setpoints = [setpoints] # to allow equal treatment of both cases
    i = 0
    for sub_setpoints in setpoints:
        segmented_setpoints.append([])
        ref_value1 = sub_setpoints[0]
        ref_value2 = sub_setpoints[0]
        for setpoint in sub_setpoints:
            if max(abs(setpoint-ref_value1), abs(setpoint-ref_value2)) > max_difference:
                i+=1
                ref_value1 = ref_value2 = setpoint
                segmented_setpoints.append([])
            segmented_setpoints[i].append(setpoint)
            ref_value1 = max(segmented_setpoints[i])
            ref_value2 = min(segmented_setpoints[i])
                
        i+=1
    return segmented_setpoints
    