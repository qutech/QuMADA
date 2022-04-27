"""
Created on Fri Mar 18 10:33:00 2022

@author: Flash
"""
import json
import operator
from typing import Mapping

import numpy as np
import pandas as pd


class ParameterDict(dict):
    """Changes operator | and |= of dict to overwrite entries, that are dict and have a key 'type'."""
    def __or__(self, other):
        new = self.__class__(**self)
        new |= other
        return new

    def __ior__(self, other):
        for key, val in other.items():
            # All low-level parameters have an entry "keys".
            # Do not merge but overwrite those entries.
            if isinstance(val, Mapping) and 'type' not in val.keys():
                self[key] = operator.ior(self.get(key, ParameterDict()), val)
            else:
                self[key] = val
        return self


def update_parameters(parameter_file, new_parameters):
    existing_parameters = json.load(parameter_file.open('r' if parameter_file.exists() else 'x'),
                                    object_pairs_hook=ParameterDict)
    parameters = existing_parameters | new_parameters
    json.dump(parameters, parameter_file.open('w'), indent=2)
    return parameters


def intialize_dac_parameter_file(mapping, parameter_file):

    parameters = ParameterDict()
    for i in range(20):
        if i in mapping.keys():
            key = mapping[i]
        else:
            key = f"CH{i}"
        parameters |= gettable_dac_entry(key)

    return update_parameters(parameter_file, parameters)


def excel_to_dac_parameter_file(excel_file, parameter_file,
                                sample_header='Sample', dac_header='DAC/AWG'):
    excel = pd.read_excel(excel_file, usecols=[sample_header, dac_header])
    mapping = ParameterDict({int(dac): sample
                             for dac, sample in zip(excel['DAC/AWG'], excel['Sample'])
                             if not np.isnan(dac)})

    return intialize_dac_parameter_file(mapping, parameter_file)


def dynamic_dac_entry(dac, start, stop, num_points=100, delay=0.025):
    return ParameterDict({
        dac: ParameterDict({
            'voltage': ParameterDict({
                'type': 'dynamic',
                'start': start,
                'stop': stop,
                'num_points': num_points,
                'delay': delay
            })
        })
    })


def static_dac_entry(dac, value, gettable=False):
    return ParameterDict({
        dac: ParameterDict({
            'voltage': ParameterDict({
                'type': 'static gettable' if gettable else 'static',
                'value': value
            })
        })
    })


def gettable_dac_entry(dac, **kwargs):
    return ParameterDict({
        dac: ParameterDict({
            'voltage': ParameterDict({
                'type': 'gettable'
            }) | kwargs
        })
    })


def static_smu_entry(smu, parameter, value, gettable=False):
    return ParameterDict({
        smu: ParameterDict({
            parameter: ParameterDict({
                'type': 'static gettable' if gettable else 'static',
                'value': value
            })
        })
    })
