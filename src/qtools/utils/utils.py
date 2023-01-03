"""
Created on Tue Aug  2 17:01:34 2022

@author: lab
"""
import numpy as np


#%%
def flatten_array(l) -> list:
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

    rec(l, results)
    return results


#%%


def _validate_mapping(
    entry, valid_entries, mapping: dict = None, default=None, default_key_error=None
):
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
            print(
                f"{mapping.get(entry)} is not in {valid_entries}. Using default value: {default}"
            )
            return default
    else:
        print(f"{entry} is not in mapping. Using default value: {default_key_error}")
        return default_key_error
