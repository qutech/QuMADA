# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of qtools.
#
# qtools is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# qtools is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# qtools. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Tobias Hangleiter


from __future__ import annotations

import json
import operator
from os import PathLike
from pathlib import Path
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


def update_parameters(
    parameter_file_path: str | PathLike, new_parameters: ParameterDict
):
    """Write or overwrite parameters to a file."""
    path = Path(parameter_file_path)
    existing_parameters = json.load(
        path.open("r" if path.exists() else "x"), object_pairs_hook=ParameterDict
    )
    parameters = existing_parameters | new_parameters
    json.dump(parameters, path.open("w"), indent=2)
    return parameters


def intialize_dac_parameter_file(mapping, parameter_file_path: str | PathLike):
    """Write new dac parameter file with dummy channels before relevant entries."""
    parameters = ParameterDict()
    for i in range(20):
        if i in mapping.keys():
            key = mapping[i]
        else:
            key = f"CH{i}"
        parameters |= gettable_dac_entry(key)

    return update_parameters(parameter_file_path, parameters)


def excel_to_dac_parameter_file(
    excel_file,
    parameter_file_path: str | PathLike,
    sample_header="Sample",
    dac_header="DAC/AWG",
):
    """Read dac parameters from Excel file and save them (with dummy channels) to new parameter file."""
    excel = pd.read_excel(excel_file, usecols=[sample_header, dac_header])
    mapping = ParameterDict({int(dac): sample
                             for dac, sample in zip(excel['DAC/AWG'], excel['Sample'])
                             if not np.isnan(dac)})

    return intialize_dac_parameter_file(mapping, parameter_file_path)


def dynamic_dac_entry(dac, start, stop, num_points=100, delay=0.025) -> ParameterDict:
    """Generate a "dynamic" dac parameter."""
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


def static_dac_entry(dac, value, gettable=False) -> ParameterDict:
    """Generate a "static" dac parameter."""
    return ParameterDict({
        dac: ParameterDict({
            'voltage': ParameterDict({
                'type': 'static gettable' if gettable else 'static',
                'value': value
            })
        })
    })


def gettable_dac_entry(dac, **kwargs) -> ParameterDict:
    """Generate a "gettable" dac parameter."""
    return ParameterDict({
        dac: ParameterDict({
            'voltage': ParameterDict({
                'type': 'gettable'
            }) | kwargs
        })
    })


def static_smu_entry(smu, parameter, value, gettable=False) -> ParameterDict:
    """Generate a static (gettable) SMU parameter."""
    return ParameterDict({
        smu: ParameterDict({
            parameter: ParameterDict({
                'type': 'static gettable' if gettable else 'static',
                'value': value
            })
        })
    })
