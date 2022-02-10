"""
Created on Fri Sep  3 13:34:00 2021
Loading data from Database
@author: Till Huckemann
"""
from __future__ import annotations

from os import path

import qcodes as qc
from qcodes.dataset.plotting import plot_dataset

import qtools as qt
from qtools.utils.browsefiles import browsefiles


#%%
def flatten_list(l: list) -> list:
    """
    Flattens nested lists
    """
    results = []
    def rec(sublist, results):
        for entry in sublist:
            if isinstance(entry, list):
                rec(entry, results)
            else:
                results.append(entry)
    rec(l, results)
    return results


#%%
def load_db(filepath: str | None = None) -> None:
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
        filetypes = (("DB Files", "*.db*"), ("All files", "*.*"))
        filepath = browsefiles(filetypes=filetypes)
        if filepath == "":
            return None
    try:
        qc.initialise_or_create_database_at(filepath)
        return None
    except Exception:
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
def _pick_sample_name() -> str:
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
def list_measurements_for_sample(sample_name: str | None = None) -> list[qc.DataSet]:
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
        qc.load_by_run_spec(sample_name=sample_name)
    except NameError:
        pass
    return _list_measurements_for_sample(sample_name)


#%%
def _list_measurements_for_sample(sample_name: str | None = None) -> list[qc.DataSet]:
    """
    Returns flattened list containing all datasets belonging to the sample specified
    """
    datasets = []
    for experiment in qc.experiments():
        if experiment.sample_name == sample_name:
            datasets.append([*(dataset for dataset in experiment.data_sets())])
    return flatten_list(datasets)


#%%
def _flatten_experiment_container() -> list[qc.DataSet]:
    """
    Returns flattened list of all datasets in the currently loaded .db
    """
    datasets = [*(experiment.data_sets() for experiment in qc.experiments())]
    return flatten_list(datasets)

#%%

def pick_measurement(sample_name: str = None, preview_dialogue = True):
    """
    Returns a measurement of your choice, plots it if you want.
    Interactive, if no sample_name is provided.
    """
    
    measurements = list_measurements_for_sample(sample_name = sample_name)
    for idx, measurement in enumerate(measurements):
        print(f"{idx} : {measurement.name}")
    chosen = int(input("Please choose a measurement: "))
    chosen_measurement = measurements[int(chosen)]
    if preview_dialogue:
        preview = str(input("Do you want to see a plot? (Y/N) "))
        if str.lower(preview) == "y":
            plot_dataset(chosen_measurement)
    return chosen_measurement

#%%

def plot_data(sample_name: str = None):
    """
    Simple plotting of datasets from the QCoDeS DB.
    """
    dataset = pick_measurement(sample_name = sample_name, preview_dialogue = False)
    independend_parameters = list()
    dependend_parameters = list()
    for parameter in dataset.get_parameters():
        if len(parameter._depends_on) == 0:
            independend_parameters.append(parameter)
        else:
            dependend_parameters.append(parameter)
    print("Which parameter do you want to plot?")
    for idx, parameter in enumerate(dependend_parameters):
        print(f"{idx} : {parameter.label}")
    plot_param_numbers = input("Please enter the numbers of the parameters you want to plot, separated by blank")
    param_list = plot_param_numbers.split()
    plot_params = list()
    for param in plot_param_numbers:
        plot_params.append(dependend_parameters[int(param)].name)
    print(plot_params)
    for param in plot_params:
        y_data = dataset.get_parameter_data(param)[param][param]
        print(dataset.get_parameter_data(param)[param])
        x_data = dataset.get_parameter_data(param)[param][dependend_parameters[0].name]
        
        print(y_data)
        print(x_data)
        