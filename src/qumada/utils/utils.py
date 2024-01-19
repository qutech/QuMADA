# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Till Huckeman
# - Daniel Grothe
# - Sionludi Lab


import numpy as np


# %%
def flatten_array(lst) -> list:
    """
    Flattens nested lists and arrays, returns flattened list
    """
    results = []

    def rec(sublist, results):
        for entry in sublist:
            if isinstance(entry, list) or isinstance(entry, np.ndarray):
                rec(entry, results)
            else:
                results.append(entry)

    rec(lst, results)
    return results


# %%


def _validate_mapping(entry, valid_entries, mapping: dict = None, default=None, default_key_error=None):
    """
    Returns mapped value with validation check.

    Parameters
    ----------
    entry : Entry to check.
    valid_entries : Allowed return items.
    mapping : Dictionary mapping the entry to a return value. The default is None (returning entry if valid)
    default : TYPE, optional
        Return value if return value is not valid. The default is None.
    default_key_error : TYPE, optional
        Return value if entry is None or not a key. The default is None.

    Returns
    -------
    Entry if mappiong is None, item mapped to key in mapping if both are valid, else default or default
    key error.

    """
    if not mapping:
        if entry in valid_entries:
            return entry
        else:
            print(f"{entry} is not in {valid_entries}. Using default value: {default}")
            return default
    if entry in mapping.keys():
        if entry in valid_entries:
            return mapping.get(entry)
        else:
            print(f"{mapping.get(entry)} is not in {valid_entries}. Using default value: {default}")
            return default
    else:
        print(f"{entry} is not in mapping. Using default value: {default_key_error}")
        return default_key_error


# %%
def naming_helper(measurement_script, default_name="Measurement"):
    """
    Handles the naming of measurements for measurement scripts.
    Uses the available name with the highest priority.
    Priorities:
        Metadata object in measurement script
        measurement_script.measurement_name
        default_name
    If measurement_script.auto_naming is True, the default name is used always!
    Changes measurement_script.measurement_name to highest priority name
    and returns it.
    If metadata object is available the name in the metadata object is also
    changed!
    """
    if measurement_script.settings.get("auto_naming", False):
        if measurement_script.metadata is not None:
            measurement_script.metadata.measurement.name = default_name
        measurement_script.measurement_name = default_name
    else:
        if measurement_script.metadata is not None:
            measurement_script.measurement_name = measurement_script.metadata.measurement.name
        elif getattr(measurement_script, "measurement_name", None) is not None:
            pass
        else:
            measurement_script.measurement_name = default_name
    return measurement_script.measurement_name
