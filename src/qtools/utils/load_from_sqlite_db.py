# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 13:34:00 2021
Loading data from Database
@author: Till Huckemann
"""

import qcodes as qc
import qtools as qt
from qtools.utils.browsefiles import browsefiles
from qcodes.dataset.plotting import plot_dataset
from os import path
#%%
def flatten_list(l: list()) -> list:
    """
    Flattens nested lists
    """
    results = list()
    def rec(sublist, results):
        for entry in sublist:
            if isinstance(entry, list):
                rec(entry, results)
            else:
                results.append(entry)
    rec(l, results)
    return results

#%%
def load_db(filepath : str = None) -> None:
    """
    Loads or creates the database.

    Parameters
    ----------
    filepath : str, optional
        Provide the path to the DB here if you want to skip the file explorer.
        The default is None.

    Returns
    -------
    None.
    #TODO: Checks only whether provided path is a file but not which type.
    """
    if not filepath or not path.isfile(filepath):
        filepath = browsefiles(filetypes = (("DB Files", "*.db*"),
                                         ("All files", "*.*")))
        if filepath == "":
            return None
    try:
        qc.initialise_or_create_database_at(filepath)
        return None
    except:
        print("Please provide a valid path")
        return load_db(None)
    
#%%
def list_sample_names()-> set[str]:
    """
    Lists all sample names that appear in the database
    """
    name_set = set(measurement.sample_name for measurement in qc.experiments())
    return name_set

#%%
def _pick_sample_name()-> str:
    """
    Lists all samples and allows the user to pick one.
    Returns String with sample name
    """
    samples = list(list_sample_names())
    print("Please choose a sample:")
    for idx, sample in enumerate(samples):
        print(f"{idx}: {sample}")
    while True:
        try:
            chosen = samples[int(input("Enter sample number: "))]
            return chosen
        except:
            print("Please chose a valid entry")
                
#%%
def list_measurements_for_sample(sample_name : str = None) -> list[qc.dataset]:
    """
    Lists all measurements done with a certain sample in the console.
    If no sample is provided it helps you to find one.
    Returns list with all datasets belonging to the sample specified.
    Parameters
    ----------
    sample_name : str, optional
        In case you do not want to do this via user input. The default is None.
    
    Returns
    -------
    list
    """
    if not sample_name:
        sample_name = _pick_sample_name()
    try:
        qc.load_by_run_spec(sample_name = sample_name)
    except NameError:
        pass
    return _list_measurements_for_sample(sample_name)

#%%
def _list_measurements_for_sample(sample_name: str = None) -> list[qc.dataset]:
    """
    Returns flattened list containing all datasets belonging to the sample specified
    """
    datasets = list()
    for experiment in qc.experiments():
        if experiment.sample_name == sample_name:
            datasets.append([*(dataset for dataset in experiment.data_sets())])
    return flatten_list(datasets)

#%%
def _flatten_experiment_container() -> list[qc.dataset]:
    """
    Returns flattened list of all datasets in the currently loaded .db
    """
    datasets = [*(experiment.data_sets() for experiment in qc.experiments())]
    return flatten_list(datasets)
    


    
    
    
    
    