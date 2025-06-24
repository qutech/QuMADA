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
# - Till Huckeman


"""
Loading data from Database
"""
from __future__ import annotations

from os import path

import numpy as np
import qcodes as qc
from qcodes.dataset.data_set import DataSet
from qcodes.dataset.plotting import plot_dataset

from qumada.utils.browsefiles import browsefiles
import re


# %%
def flatten_list(lst: list) -> list:
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

    rec(lst, results)
    return results


# %%
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
    if not filepath:
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
    elif not path.isfile(filepath):
        try:
            qc.initialise_or_create_database_at(filepath)
            print("Created new Database")
            return None
        except Exception as e:
            print("Please provide a valid path")
            raise e
    else:
        try:
            qc.initialise_or_create_database_at(filepath)
        except Exception:
            print("The file you want to load is no valid db file!")
            return load_db(None)


# %%
def list_sample_names() -> set[str]:
    """
    Lists all sample names that appear in the database
    """
    name_set = {measurement.sample_name for measurement in qc.experiments()}
    return name_set


# %%
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
        except Exception:
            print("Please chose a valid entry")


# %%
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


# %%
def _list_measurements_for_sample(sample_name: str | None = None) -> list[qc.DataSet]:
    """
    Returns flattened list containing all datasets belonging to the sample specified
    """
    datasets = []
    for experiment in qc.experiments():
        if experiment.sample_name == sample_name:
            datasets.append([*(dataset for dataset in experiment.data_sets())])
    return flatten_list(datasets)


# %%
def _flatten_experiment_container() -> list[qc.DataSet]:
    """
    Returns flattened list of all datasets in the currently loaded .db
    """
    datasets = [*(experiment.data_sets() for experiment in qc.experiments())]
    return flatten_list(datasets)


# %%


def pick_measurement(sample_name: str = None, preview_dialogue=True):
    """
    Returns a measurement of your choice, plots it if you want.
    Interactive, if no sample_name is provided.
    """

    measurements = list_measurements_for_sample(sample_name=sample_name)
    for idx, measurement in enumerate(measurements):
        print(f"{idx} (Run ID {measurement.run_id}) : {measurement.name}")
    chosen = int(input("Please choose a measurement: "))
    chosen_measurement = measurements[int(chosen)]
    if preview_dialogue:
        preview = str(input("Do you want to see a plot? (Y/N) "))
        if str.lower(preview) == "y":
            plot_dataset(chosen_measurement)
    return chosen_measurement


# %%


def pick_measurements(sample_name: str = None, preview_dialogue=False, measurement_list=None):
    """
    Returns a measurement of your choice, plots it if you want.
    Interactive, if no sample_name is provided.
    """

    pattern = r"^\s*(\d+)\s*-\s*(\d+)\s*$"
    if not measurement_list:
        measurement_list = list()
    measurements = list_measurements_for_sample(sample_name=sample_name)
    for idx, measurement in enumerate(measurements):
        print(f"{idx} (Run ID {measurement.run_id}) : {measurement.name}")
    print("Please add a measurement by selecting its number or providing a range '(Number1-Number2)'")
    while True:
        chosen = input("Please choose a measurement: ")
        match = re.match(pattern, chosen)
        if chosen == "f":
            return measurement_list
        elif chosen == "s":
            return pick_measurements(preview_dialogue=preview_dialogue, measurement_list=measurement_list)
        elif chosen == "l":
            load_db()
            return pick_measurements(preview_dialogue=preview_dialogue, measurement_list=measurement_list)
        elif re.match(pattern, chosen):
            for i in range(int(match.group(1)), int(match.group(2))+1):
                measurement_list.append(measurements[i])
        else:
            chosen = int(chosen)
            measurement_list.append(measurements[int(chosen)])
        print("Please enter 'f' when your are finished or 's' if you want to add measurements of another sample")
        print("Type 'l' to open the load database menu in order to select a different database.")


# %%


def plot_data(sample_name: str = None):
    """
    Simple plotting of datasets from the QCoDeS DB.
    """
    dataset = pick_measurement(sample_name=sample_name, preview_dialogue=False)
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


# %%
def get_parameter_data(dataset=None, parameter_name=None, **kwargs):
    """
    Gets you the data for a chosen dependent parameter and the data of the first (!)
    parameter it depends on
    #TODO: Support for independent parameters
    """
    if not dataset:
        dataset = pick_measurement()
    if not isinstance(dataset, DataSet):
        print("Dataset has to be of type DataSet")
        return None
    if not parameter_name:
        for idx, parameter in enumerate(dataset.dependent_parameters):
            print(f"{idx} : {parameter.label} / {parameter.name}")
        chosen_param_num = int(input("Please enter number: "))
        chosen_param = dataset.dependent_parameters[chosen_param_num]
        parameter_name = chosen_param.name
    else:
        chosen_param = dataset.paramspecs[parameter_name]
    independent_param = dataset.paramspecs[parameter_name]._depends_on
    # if not isinstance(independent_param, str):
    #     independent_param = independent_param[0]
    params = (*independent_param, parameter_name)
    labels = (*(dataset.paramspecs[i_p].label for i_p in independent_param), chosen_param.label)
    units = (*(dataset.paramspecs[i_p].unit for i_p in independent_param), chosen_param.unit)
    data = (
        *tuple(dataset.get_parameter_data(parameter_name)[parameter_name][param] for param in independent_param),
        dataset.get_parameter_data(parameter_name)[parameter_name][parameter_name],
    )
    return zip(params, data, units, labels)

# %%

def get_parameter_name_by_label(dataset=None, parameter_label=None, appendix = ""):
    for param in dataset.get_parameters():
        if param.label == parameter_label + appendix:
            return param.name
    return None

# %%
def separate_up_down(x_data, y_data):
    grad = np.gradient(x_data)
    curr_sign = np.sign(grad[0])
    data_list_x = list()
    data_list_y = list()
    direction = list()
    direction.append(curr_sign)
    start_helper = 0
    for i in range(0, len(grad)):
        if np.sign(grad[i]) != curr_sign:
            data_list_x.append(x_data[start_helper:i])
            data_list_y.append(y_data[start_helper:i])
            start_helper = i + 1
            curr_sign = np.sign(grad[i])
            direction.append(curr_sign)
    data_list_x.append(x_data[start_helper : len(grad)])
    data_list_y.append(y_data[start_helper : len(grad)])
    if len(direction) == 0:
        direction.append(1)
    return data_list_x, data_list_y, direction
