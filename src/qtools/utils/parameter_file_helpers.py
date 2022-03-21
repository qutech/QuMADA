# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 10:33:00 2022

@author: Flash
"""
from typing import Mapping

import numpy as np
from collections import OrderedDict
import json
import pandas as pd


def update_dict_recursively(dct, new):
    for key, val in new.items():
        if isinstance(val, Mapping):
            dct[key] = update_dict_recursively(dct.get(key, {}), val)
        else:
            dct[key] = val
    return dct


def update_parameters(parameter_file, new_parameters):
    existing_parameters = json.load(parameter_file.open('r' if parameter_file.exists() else 'x'),
                                    object_pairs_hook=OrderedDict)
    parameters = update_dict_recursively(existing_parameters, new_parameters)
    json.dump(parameters, parameter_file.open('w'), indent=2)
    return parameters


def intialize_dac_parameter_file(mapping, parameter_file):

    parameters = OrderedDict()
    for i in range(20):
        if i in mapping.keys():
            key = mapping[i]
        else:
            key = f"CH{i}"
        parameters |= gettable_gate_entry(key)

    return update_parameters(parameter_file, parameters)


def excel_to_dac_parameter_file(excel_file, parameter_file,
                              gate_header='Sample', dac_header='DAC/AWG'):
    excel = pd.read_excel(excel_file, usecols=[gate_header, dac_header])
    mapping = {int(dac): sample for dac, sample in zip(excel['DAC/AWG'], excel['Sample'])
               if not np.isnan(dac)}

    return intialize_dac_parameter_file(mapping, parameter_file)


def dynamic_gate_entry(gate, start, stop, num_points=100, delay=0.025):
    return {
        gate: {
            'voltage': {
                'type': 'dynamic',
                'start': start,
                'stop': stop,
                'num_points': num_points,
                'delay': delay
            }
        }
    }


def static_gate_entry(gate, value):
    return {
        gate: {
            'voltage': {
                'type': 'static',
                'value': value
            }
        }
    }


def gettable_gate_entry(gate, **kwargs):
    return {
        gate: {
            'voltage': {
                'type': 'gettable'
            } | kwargs
        }
    }


def static_smu_entry(smu, parameter, value):
    return {
        smu: {
            parameter: {
                'type': 'static',
                'value': value
            }
        }
    }
