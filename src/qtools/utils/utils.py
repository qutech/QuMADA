# -*- coding: utf-8 -*-
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