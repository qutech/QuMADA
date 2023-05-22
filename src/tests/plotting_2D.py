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
# - Sionludi Lab
# - Till Huckeman


import qcodes as qc
import qtools as qt
from qtools.utils.load_from_sqlite_db import *
from qtools.utils.browsefiles import browsefiles
from qcodes.dataset.plotting import plot_dataset
from qcodes.dataset.data_export import reshape_2D_data
#from qtools.instrument.mapping.base import flatten_list
import numpy as np
from matplotlib import pyplot as plt
import matplotlib

#%%
def _handle_overload(*args, 
                     output_dimension : int = 1,
                     x_name = None,
                     y_name = None,
                     z_name = None,
                     **kwargs):
    """
    Reduces the amount of input parameters to output_dimension according to
    user input.
    """
    all_params = list(args)
    params = [None for i in range(output_dimension)]
    if len(all_params) == output_dimension:
        return all_params
    if x_name:
        for i, param in enumerate(all_params):
            if param[0] == x_name:
                params[0]=all_params.pop(i)
                output_dimension-=1
    if y_name:
        for i, param in enumerate(all_params):
            if param[0] == y_name:
                params[1]=all_params.pop(i)
                output_dimension-=1
    if z_name:
        for i, param in enumerate(all_params):
            if param[0] == z_name:
                params[2]=all_params.pop(i)  
                output_dimension-=1
    
    print(f"To many parameters found. Please choose {output_dimension} parameter(s)")
    for i in range(0, output_dimension):       
        for idx, j in enumerate(all_params):
            print(f"{idx} : {j[0]}")
        choice = input("Please enter ID: ")
        for k in range(len(params)):
            if not params[k]:
                params[k] = all_params.pop(int(choice))
    return params

    #%%
def plot_2D(x_data, y_data, z_data, *args, **kwargs):
    """
    Plots 2D derivatives. Requires tuples of name and 1D arrays corresponding 
    to x, y and z data as input. 
    Works well with Qtools "get_parameter_data" method found in
    load_from_sqlite.

    TODO: Add get_parameter_data method as default to call when no data is provided
    TODO: Add further image manipulation and line detection functionality
    """
    if args:
        x_data, y_data, z_data=_handle_overload(x_data, y_data, z_data, *args, 
                                                output_dimension=3)
    fig, ax = plt.subplots()
    x, y, z = reshape_2D_data(x_data[1], y_data[1], z_data[1])
    im = plt.pcolormesh(x, y, z)
    fig.colorbar(im, ax = ax, label = f"{x_data[0]} in {z_data[2]}")
    plt.xlabel(f"{x_data[0]} in {x_data[2]}")
    plt.ylabel(f"{y_data[0]} in {y_data[2]}")
    plt.show()
    return fig, ax


#%%
def plot_2D_grad(x_data, y_data, z_data, *args, direction = "both"):
    """
    Plots 2D derivatives. Requires tuples of name and 1D arrays corresponding 
    to x, y and z data as input. 
    Works well with Qtools "get_parameter_data" method found in load_from_sqlite.
    direction argument can be x, y or z corresponding to the direction of the 
    gradient used. "both" adds the gradients quadratically.

    TODO: Add get_parameter_data method as default to call when no data is provided
    TODO: Add further image manipulation and line detection functionality    
    """
    if args:
        x_data, y_data, z_data=_handle_overload(x_data, y_data, z_data, *args, 
                                                output_dimension=3)
    fig, ax = plt.subplots()
    x, y, z = reshape_2D_data(x_data[1], y_data[1], z_data[1])
    z_gradient = np.gradient(z, x, y)
    if direction == "both":
        grad = np.sqrt(z_gradient[0]**2+z_gradient[1]**2)
    elif direction == "x":
        grad = z_gradient[0]
    elif direction == "y":
        grad = z_gradient[1]
    im = plt.pcolormesh(x, y, grad)
    fig.colorbar(im, ax = ax, label = f"Gradient of {z_data[0]} in {z_data[2]}/{x_data[2]}")
    plt.xlabel(f"{x_data[0]} in {x_data[2]}")
    plt.ylabel(f"{y_data[0]} in {y_data[2]}")
    plt.show()
    return fig, ax

#%%
def plot_2D_sec_derivative(x_data, y_data, z_data, *args):
    """
    Plots second derivative of data.
    Requires tuples of name and 1D arrays corresponding 
    to x, y and z data as input. 
    Works well with Qtools "get_parameter_data" method found in load_from_sqlite.
    direction argument can be x, y or z corresponding to the direction of the 
    gradient used. "both" adds the gradients quadratically.

    TODO: Add get_parameter_data method as default to call when no data is provided
    TODO: Add further image manipulation and line detection functionality   
    """
    if args:
        x_data, y_data, z_data=_handle_overload(x_data, y_data, z_data, *args, 
                                                output_dimension=3)
    fig, ax = plt.subplots()
    x, y, z = reshape_2D_data(x_data[1], y_data[1], z_data[1])
    z_gradient = np.gradient(z, x, y)
    z_g_x = np.gradient(z_gradient[0], x, y)
    z_g_y = np.gradient(z_gradient[1], x, y)
    grad2 = np.sqrt(z_g_x[0]**2 + z_g_y[1]**2 + 2 *z_g_x[1]*z_g_y[0])
    im = plt.pcolormesh(x, y, grad2)
    fig.colorbar(im, ax = ax, label = "2nd Derivative of {z[1]}")
    plt.xlabel(f"{x_data[0]} in {x_data[2]}")
    plt.ylabel(f"{y_data[0]} in {y_data[2]}")
    plt.show()
    return fig, ax
#%%
def plot_hysteresis(dataset,
                    x_name,
                    y_name):
    fig, ax = plt.subplots()
    grad = np.gradient(dataset[x_name])
    curr_sign = np.sign(grad[0])
    data_list_x = list()
    data_list_y = list()
    start_helper = 0
    for i in range(0, len(grad)):

        if np.sign(grad[i]) != curr_sign:
            data_list_x.append(dataset[x_name][start_helper:i])
            data_list_y.append(dataset[y_name][start_helper:i])
            start_helper = i+1
            curr_sign = np.sign(grad[i])
    data_list_x.append(dataset[x_name][start_helper:len(grad)])
    data_list_y.append(dataset[y_name][start_helper:len(grad)])
            
            


            
    for i in range(0, len(data_list_x)):
        plt.plot(data_list_x[i], data_list_y[i])
    plt.show()
    return fig, ax

#%%

def plot_hysteresis_new(x_data,
                    y_data):
    fig, ax = plt.subplots()
    grad = np.gradient(x_data[1])
    curr_sign = np.sign(grad[0])
    signs = [curr_sign]
    data_list_x = list()
    data_list_y = list()
    start_helper = 0
    for i in range(0, len(grad)):

        if np.sign(grad[i]) != curr_sign:
            data_list_x.append(x_data[1][start_helper:i])
            data_list_y.append(y_data[1][start_helper:i])
            start_helper = i+1
            curr_sign = np.sign(grad[i])
            signs.append(curr_sign)
    data_list_x.append(x_data[1][start_helper:len(grad)])
    data_list_y.append(y_data[1][start_helper:len(grad)])

    for i in range(0, len(data_list_x)):
        options = {
            -1 : "v",
            1 : "^"
            }
        plt.plot(data_list_x[i], data_list_y[i], options[signs[i]])
    plt.show()
    return fig, ax

#%%
def plot_multiple_datasets(datasets : list = None,
                               x_axis_parameters_name: str = None,
                               y_axis_parameters_name: str = None,
                               plot_hysteresis: bool = True,
                               **kwargs):
    """
    Allows plotting of multiple datasets from a qcodes database into one plot.
    So far, only 2D plotting is supported. Takes care of labels and legend.

    Parameters
    ----------
    datasets : list, optional
        List of Qtools datasets. If set to None, you can pick measurements from
        the currently loaded Qtools database. Default is None.
    x_axis_parameters_name : str, optional
        Pass the namestring of the parameter you want to plot on the x-axis. 
        If none, you will be asked to set it individually for every chosen
        dataset, if more than two parameters are in the dataset.
        The default is None.
    y_axis_parameters_name : str, optional
        Pass the namestring of the parameter you want to plot on the y-axis. 
        If none, you will be asked to set it individually for every chosen
        dataset, if more than two parameters are in the dataset.
        The default is None.
    plot_hysteresis : bool, optional
        Will separate datasets that contain multiple sweeps into multiple
        graphs, based on the monotony of the x-axis parameters data. 
        The default is True.
    **kwargs : TYPE
        DESCRIPTION.

    Returns
    -------
    fig : pyplot Figure object.
    ax : pyplot axis objects.
    
    TODO: Move pyplot plot settings into kwargs.
    """
    if not datasets:
        print("hello, I am empty")
        datasets = pick_measurements()
    x_data = list()
    y_data = list()
    signs = list()
    x_units = list()
    y_units = list()
    matplotlib.rc('font', size = 35)
    fig, ax = plt.subplots(figsize=(30, 30))
    x_labels = []
    y_labels = []
    for i in range(len(datasets)):
        label = datasets[i].name
        x, y = _handle_overload(*get_parameter_data(datasets[i], y_axis_parameters_name),
                                x_name= x_axis_parameters_name,
                                y_name= y_axis_parameters_name,
                                output_dimension=2)
        x_data.append(x[1]) #This is the x_data
        y_data.append(y[1]) #This is the y_data
        x_labels.append(x[3]) #Labels of x_data
        y_labels.append(y[3]) #Labels of y_data
        x_units.append(x[2]) #Units of x_data
        y_units.append(y[2]) #Units of y_data

        if plot_hysteresis:
            x_s, y_s, signs = separate_up_down(x_data[i], y_data[i])
            for j in range(len(x_s)):
                if signs[j] == 1:
                    marker ="^"
                    f_label =f"{label} foresweep"
                    f_label = f_label.replace("Gate ", "")
                else:
                    marker = "v"
                    f_label = f"{label} backsweep"
                    f_label =f_label.replace("Gate ", "")
                if j > 0:
                    p = plt.plot(x_s[j], y_s[j], marker, 
                                 color = p[-1].get_color(), 
                                 label = f_label, 
                                 markersize = kwargs.get("markersize", 15))
                else:
                    p = plt.plot(x_s[j], y_s[j], 
                                 marker, 
                                 label = f_label, 
                                 markersize = kwargs.get("markersize", 15))
        else:
            p = plt.plot(x_data[i], y_data[i], 
                         marker = kwargs.get("marker", "."), 
                         label = label, 
                         markersize = kwargs.get("markersize", 15))
    plt.xlabel(f"{x_labels[0]} ({x_units[0]})")
    plt.ylabel(f"{y_labels[0]} ({y_units[0]})")
    plt.legend(loc = "upper left",
               fontsize = kwargs.get("legend_fontsize", 15),
               markerscale = kwargs.get("legend_markerscale", 1))
    plt.tight_layout()

    return fig, ax
    
#%%

def separate_up_down_old(x_data, y_data):

    grad = np.gradient(x_data)
    curr_sign = np.sign(grad[0])
    data_list_x = list()
    data_list_y = list()
    start_helper = 0
    for i in range(0, len(grad)):
        if np.sign(grad[i]) != curr_sign:
            data_list_x.append(x_data[start_helper:i])
            data_list_y.append(y_data[start_helper:i])
            start_helper = i+1
            curr_sign = np.sign(grad[i])
    data_list_x.append(x_data[start_helper:len(grad)])
    data_list_y.append(y_data[start_helper:len(grad)])
    
    return data_list_x, data_list_y

#%%
def hysteresis(dataset, I_threshold = 15e-12, parameter_name = "lockin_current"):
    
    data = list(get_parameter_data(dataset = dataset, parameter_name = parameter_name))
    voltage = data[0][1]
    current = data[1][1]
    v, c = separate_up_down_old(voltage, current)
    for i in range(0, len(v[0])):
        if c[0][i] >= I_threshold:
            V_threshold_up = v[0][i]
            break
    for i in range(0, len(v[1])):
        if c[1][i] <= I_threshold:
            V_threshold_down = v[1][i]
            break
    return V_threshold_up, V_threshold_down
