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
# - Sionludi Lab
# - Till Huckeman
# %%

import matplotlib
import matplotlib.ticker as ticker

# from qumada.instrument.mapping.base import flatten_list
import numpy as np
from matplotlib import pyplot as plt
from qcodes.dataset.data_export import reshape_2D_data

from qumada.utils.load_from_sqlite_db import (
    get_parameter_data,
    pick_measurements,
    separate_up_down,
)


# %%
def _handle_overload(*args, output_dimension: int = 1, x_name=None, y_name=None, z_name=None, **kwargs):
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
                params[0] = all_params.pop(i)
                output_dimension -= 1
    if y_name:
        for i, param in enumerate(all_params):
            if param[0] == y_name:
                params[1] = all_params.pop(i)
                output_dimension -= 1
    if z_name:
        for i, param in enumerate(all_params):
            if param[0] == z_name:
                params[2] = all_params.pop(i)
                output_dimension -= 1

    print(f"To many parameters found. Please choose {output_dimension} parameter(s)")
    for i in range(0, output_dimension):
        for idx, j in enumerate(all_params):
            print(f"{idx} : {j[0]}")
        choice = input("Please enter ID: ")
        for k in range(len(params)):
            if not params[k]:
                params[k] = all_params.pop(int(choice))
    return params


def _get_scaled_unit_and_factor(unit: str, values: list):
    """
    Determines the best scaling factor and prefix for the given values.
    """
    prefixes = {-12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}
    abs_max_value = max(abs(min(values)), abs(max(values)))
    exponent = int(np.floor(np.log10(abs_max_value)) // 3 * 3) if abs_max_value != 0 else 0
    prefix = prefixes.get(exponent, "")
    scaling_factor = 10 ** (-exponent)
    return scaling_factor, f"{prefix}{unit}"


def _rescale_axis(axis, data, unit, axis_type="x"):
    """
    Rescales the axis ticks to avoid scientific notation and sets appropriate labels.
    """
    factor, scaled_unit = _get_scaled_unit_and_factor(unit, data)
    axis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x * factor:.1f}"))
    return factor, scaled_unit


def get_parameter_name_by_label(dataset, label):
    """
    Returns the parameter name for a given parameter label in a QCoDeS dataset.

    Parameters
    ----------
    dataset : qcodes.dataset
        The QCoDeS dataset containing the parameters.
    label : str
        The label of the parameter for which to find the name.

    Returns
    -------
    str
        The name of the parameter corresponding to the provided label.

    Raises
    ------
    ValueError
        If no parameter matches the label or if multiple parameters share the same label.
    """
    matching_parameters = []

    # Iterate over all parameters in the dataset and compare labels
    for parameter in dataset.get_parameters():
        if parameter.label == label:
            matching_parameters.append(parameter.name)

    # Handle different cases
    if not matching_parameters:
        raise ValueError(f"No parameter found with label '{label}'.")
    elif len(matching_parameters) > 1:
        raise ValueError(f"Multiple parameters found with label '{label}': {matching_parameters}")
    else:
        return matching_parameters[0]


def plot_2D(
    x_data,
    y_data,
    z_data,
    fig=None,
    ax=None,
    x_label=None,
    y_label=None,
    z_label=None,
    scale_axis=True,
    save_to_file=None,
    close=False,
    *args,
    **kwargs,
):
    """
    Plots 2D scans. Requires tuples of name and 1D arrays corresponding
    to x, y, and z data as input. Supports axis and colorbar scaling.
    Use plot_2D(*get_parameter_data()) to open interactive guide to select measurements.

    Parameters
    ----------
    x_data, y_data, z_data : tuple
        Tuples containing name, values, units, and labels of x, y, and z axes.
    fig : matplotlib.figure.Figure, optional
        The figure object. Default is None.
    ax : matplotlib.axes.Axes, optional
        The axis object. Default is None.
    x_label, y_label, z_label : str, optional
        Custom axis labels. Default is None.
    scale_axis : bool, optional
        If True, rescales axes and colorbar to use SI prefixes. Default is True.
    *args, **kwargs
        Additional arguments for flexibility.

    Returns
    -------
    fig, ax : tuple
        The figure and axis objects for further customization.
    """
    if args:
        x_data, y_data, z_data = _handle_overload(x_data, y_data, z_data, *args, output_dimension=3)
    if ax is None or fig is None:
        fig, ax = plt.subplots(figsize = kwargs.get("figsize", (10,10)))

    # Skalierung der Achsendaten und Einheiten
    x_values, y_values, z_values = x_data[1], y_data[1], z_data[1]
    x_unit, y_unit, z_unit = x_data[2], y_data[2], z_data[2]

    if scale_axis:
        x_scale, scaled_x_unit = _get_scaled_unit_and_factor(x_unit, x_values)
        y_scale, scaled_y_unit = _get_scaled_unit_and_factor(y_unit, y_values)
        z_scale, scaled_z_unit = _get_scaled_unit_and_factor(z_unit, z_values)

        # Skaliere die Daten
        x_values = np.array(x_values) * x_scale
        y_values = np.array(y_values) * y_scale
        z_values = np.array(z_values) * z_scale

        # Aktualisiere die Einheiten
        x_unit, y_unit, z_unit = scaled_x_unit, scaled_y_unit, scaled_z_unit

    # Reshape der Daten für 2D-Darstellung
    x, y, z = reshape_2D_data(x_values, y_values, z_values)

    # Plotten der 2D-Daten
    im = ax.pcolormesh(x, y, z, shading="auto")
    cbar = fig.colorbar(im, ax=ax)
    
    if z_label is None:
        cbar.set_label(f"{z_data[3]} ({z_unit})")
    else:
        cbar.set_label(f"{z_label} ({z_unit})")

    # Achsentitel aktualisieren
    x_label = x_label or f"{x_data[3]} ({x_unit})"
    y_label = y_label or f"{y_data[3]} ({y_unit})"

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    plt.tight_layout()
    plt.show()
    if save_to_file is not None:
        plt.savefig(save_to_file)
    if close is True:
        plt.close()
    return fig, ax


# %%
def plot_2D_grad(x_data, y_data, z_data, *args, direction="both"):
    """
    Plots 2D derivatives. Requires tuples of name and 1D arrays corresponding
    to x, y and z data as input.
    Works well with QuMADA "get_parameter_data" method found in load_from_sqlite.
    direction argument can be x, y or z corresponding to the direction of the
    gradient used. "both" adds the gradients quadratically.

    TODO: Add get_parameter_data method as default to call when no data is provided
    TODO: Add further image manipulation and line detection functionality
    """
    if args:
        x_data, y_data, z_data = _handle_overload(x_data, y_data, z_data, *args, output_dimension=3)
    fig, ax = plt.subplots()
    x, y, z = reshape_2D_data(x_data[1], y_data[1], z_data[1])
    z_gradient = np.gradient(z, x, y)
    if direction == "both":
        grad = np.sqrt(z_gradient[0] ** 2 + z_gradient[1] ** 2)
    elif direction == "x":
        grad = z_gradient[0]
    elif direction == "y":
        grad = z_gradient[1]
    im = plt.pcolormesh(x, y, grad)
    fig.colorbar(im, ax=ax, label=f"Gradient of {z_data[0]} in {z_data[2]}/{x_data[2]}")
    plt.xlabel(f"{x_data[0]} in {x_data[2]}")
    plt.ylabel(f"{y_data[0]} in {y_data[2]}")
    plt.show()
    return fig, ax


# %%
def plot_2D_sec_derivative(x_data, y_data, z_data, *args):
    """
    Plots second derivative of data.
    Requires tuples of name and 1D arrays corresponding
    to x, y and z data as input.
    Works well with QuMADA "get_parameter_data" method found in load_from_sqlite.
    direction argument can be x, y or z corresponding to the direction of the
    gradient used. "both" adds the gradients quadratically.

    TODO: Add get_parameter_data method as default to call when no data is provided
    TODO: Add further image manipulation and line detection functionality
    """
    if args:
        x_data, y_data, z_data = _handle_overload(x_data, y_data, z_data, *args, output_dimension=3)
    fig, ax = plt.subplots()
    x, y, z = reshape_2D_data(x_data[1], y_data[1], z_data[1])
    z_gradient = np.gradient(z, x, y)
    z_g_x = np.gradient(z_gradient[0], x, y)
    z_g_y = np.gradient(z_gradient[1], x, y)
    grad2 = np.sqrt(z_g_x[0] ** 2 + z_g_y[1] ** 2 + 2 * z_g_x[1] * z_g_y[0])
    im = plt.pcolormesh(x, y, grad2)
    fig.colorbar(im, ax=ax, label="2nd Derivative of {z[1]}")
    plt.xlabel(f"{x_data[0]} in {x_data[2]}")
    plt.ylabel(f"{y_data[0]} in {y_data[2]}")
    plt.show()
    return fig, ax


# %%
def plot_hysteresis(dataset, x_name, y_name):
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
            start_helper = i + 1
            curr_sign = np.sign(grad[i])
    data_list_x.append(dataset[x_name][start_helper : len(grad)])
    data_list_y.append(dataset[y_name][start_helper : len(grad)])

    for i in range(0, len(data_list_x)):
        plt.plot(data_list_x[i], data_list_y[i])
    plt.show()
    return fig, ax


# %%
def plot_hysteresis_new(x_data, y_data):
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
            start_helper = i + 1
            curr_sign = np.sign(grad[i])
            signs.append(curr_sign)
    data_list_x.append(x_data[1][start_helper : len(grad)])
    data_list_y.append(y_data[1][start_helper : len(grad)])

    for i in range(0, len(data_list_x)):
        options = {-1: "v", 1: "^"}
        plt.plot(data_list_x[i], data_list_y[i], options[signs[i]])
    plt.show()
    return fig, ax


# %%


def plot_multiple_datasets(
    datasets: list = None,
    x_axis_parameters_name: str = None,
    y_axis_parameters_name: str = None,
    plot_hysteresis: bool = True,
    optimize_hysteresis_legend: bool = True,
    ax=None,
    fig=None,
    scale_axis=True,
    legend=True,
    exclude_string_from_legend: list = ["1D Sweep"],
    legend_entries: None|list = None,
    save_to_file = None,
    close = False,
    x_label = None,
    y_label = None,
    color_map = None,
    **kwargs,
):
    """
    Plot multiple datasets from a QCoDeS database into a single figure.

    This function supports plotting and can handle multiple datasets.
    It automatically manages axis labels, legends, and optionally rescales the axes
    to use appropriate SI prefixes (e.g., µA, mV) instead of scientific notation.

    Parameters
    ----------
    datasets : list, optional
        List of QCoDeS datasets to plot. If None, the function allows you to pick
        measurements from the currently loaded QCoDeS database. Default is None.
    x_axis_parameters_name : str or list, optional
        The name(s) of the parameter(s) to use for the x-axis. If None, you will be prompted
        to select it individually for each dataset if more than one parameter exists.
        Default is None.
    y_axis_parameters_name : str or list, optional
        The name(s) of the parameter(s) to use for the y-axis. If None, you will be prompted
        to select it individually for each dataset if more than one parameter exists.
        Default is None.
    plot_hysteresis : bool, optional
        If True, separates datasets with multiple sweeps into different curves based
        on the monotonicity of the x-axis data. For example, foresweep and backsweep
        can be plotted with distinct markers. Default is True.
    optimize_hysteresis_legend : bool, optional
        If True, only one entry is added for each measurement instead of two for fore-
        and backsweep. Default is True.
    ax : matplotlib.axes._axes.Axes, optional
        Matplotlib axis to plot on. If None, a new figure and axis will be created.
        Default is None.
    fig : matplotlib.figure.Figure, optional
        Matplotlib figure object. Required if `ax` is provided. Default is None.
    scale_axis : bool, optional
        If True, rescales the x- and y-axes to use SI prefixes (e.g., µ, m, k) instead
        of scientific notation for better readability. Default is True.
    legend : bool, optional
        If True, legend is plotted. Default is True.
    legend_entries : None|list[str], optional
        List of custom legend entries. If None, the measurement name is used.
        Defauls it None.
    save_to_file: str|None, optional.
        Path and Filename to save plot to. Not saved if None. Default is None.
    close : bool, optional.
        If true plots are closed automatically before the function exits (e.g. in case
        you just want to save the plot to a file.) Default is False.
    x_label : str|None, optional.
        Overrides automatically generated x label. Units are still added automatically.
        Default is None.
    y_label : str|None, optional.
        Overrides automatically generated y label. Units are still added automatically.
        Default is None.
    color_map : Colormap|None, optional.
        Alternative colormap used for the plots. None uses the matplotlib default colormap.
        Default is None.
    **kwargs : dict
        Additional keyword arguments for customizing the plot. For example:
            - font: int, font size for the plot.
            - marker: str, marker style for the data points.
            - markersize: int, size of the markers.
            - legend_fontsize: int, font size for the legend.
            - legend_markerscale: float, scale factor for legend markers.
            - legend_position: str, Position of legend (passed on to matplotlib).
              Default is "upper left"
            - legend_ncols: int, Number of legend columns. Default is depending
                            on number of entries
            - legend_columnspacing: float, Spacing between legend columns
            - legend_handletextpad: float, Spacing between legend text and marker.

    Returns
    -------
    ax : matplotlib.axes._axes.Axes
        The axis object containing the plotted data.

    Notes
    -----
    - This function assumes the input datasets are from QCoDeS and compatible with
      the `get_parameter_data` function.
    - Axis scaling is applied only when `scale_axis` is True, and the scaling factor
      is calculated based on the data range.
    - Monotonicity of the x-axis is used to detect and separate hysteresis loops.

    """

    if not datasets:
        datasets = pick_measurements()
    x_data = list()
    y_data = list()
    x_units = list()
    y_units = list()
    font = kwargs.get("font", None)
    if font is not None:
        matplotlib.rc("font", 30)
    matplotlib.rc("font", size=40)
    default_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    if ax is None or fig is None:
        fig, ax = plt.subplots(figsize = kwargs.get("figsize", (10, 10)))

    x_labels = []
    y_labels = []
    for i in range(len(datasets)):
        if color_map is None:
            color = default_colors[i % len(default_colors)] 
        else:
            color = color_map[i]
        if legend_entries is None:
            label = datasets[i].name
        else:
            label = legend_entries[i]
        for string in exclude_string_from_legend:
            label = label.replace(string, "")

        if isinstance(x_axis_parameters_name, list):
            x_name = x_axis_parameters_name[i]
        else:
            x_name = x_axis_parameters_name
            
        if isinstance(y_axis_parameters_name, list):
            y_name = y_axis_parameters_name[i]
        else:
            y_name = y_axis_parameters_name
        
        x, y = _handle_overload(
            *get_parameter_data(datasets[i], y_axis_parameters_name),
            x_name=x_name,
            y_name=y_name,
            output_dimension=2,
        )
        x_data.append(x[1])
        y_data.append(y[1])
        x_labels.append(x[3])
        y_labels.append(y[3])
        x_units.append(x[2])
        y_units.append(y[2])

        if plot_hysteresis:
            x_s, y_s, signs = separate_up_down(x_data[i], y_data[i])
            for j in range(len(x_s)):
                if signs[j] == 1:
                    marker = "^"
                    f_label = f"{label}"
                    if not optimize_hysteresis_legend:
                        f_label += " foresweep"
                else:
                    marker = "v"
                    f_label = f"{label}"
                    if not optimize_hysteresis_legend:
                        f_label += " backsweep"
                if optimize_hysteresis_legend is True:
                # Only one legend entry per dataset (instead of one for each fore-/backsweep)
                    if j > 0:
                        f_label = None
                if j%2 == False: # ;-) Ensuring the first sweep marker is always filled
                    fill_style = "full"
                else:
                    fill_style = "none"

                plt.plot(
                    x_s[j],
                    y_s[j],
                    marker,
                    linestyle=kwargs.get("linestyle", ""),
                    label=f_label,
                    markersize=kwargs.get("markersize", 20),
                    color = color,
                    fillstyle = fill_style
                )
        else:
            plt.plot(
                x_data[i],
                y_data[i],
                marker=kwargs.get("marker", "."),
                linestyle=kwargs.get("linestyle", ""),
                label=label,
                markersize=kwargs.get("markersize", 20),
                color = color,
            )

    # Scale axes and update labels
    if scale_axis is True:
        x_scaling_factor, x_units[0] = _rescale_axis(ax.xaxis, np.concatenate(x_data), x_units[0], "x")
        y_scaling_factor, y_units[0] = _rescale_axis(ax.yaxis, np.concatenate(y_data), y_units[0], "y")
    
    if x_label is None:
        plt.xlabel(f"{x_labels[0]} ({x_units[0]})")
    else:
        plt.xlabel(f"{x_label} ({x_units[0]})")
    if y_label is None:
        plt.ylabel(f"{y_labels[0]} ({y_units[0]})")
    else:
        plt.ylabel(f"{y_label} ({y_units[0]})")
        
    # Update x and y labels
    leg_entries = ax.legend().get_texts()
    if legend is True:
        plt.legend(
            loc=kwargs.get("legend_position", "upper left"),
            fontsize=kwargs.get("legend_fontsize", 35),
            markerscale=kwargs.get("legend_markerscale", 1),
            ncol = kwargs.get("legend_ncols", int(len(leg_entries)/9)+1),
            columnspacing = kwargs.get("legend_columnspacing", 0.2),
            handletextpad = kwargs.get("legend_handletextpad", -0.7),
        )
    plt.tight_layout()
    if save_to_file is not None:
        plt.savefig(save_to_file)
    if close is True:
        plt.close()
    return fig, ax


# %%


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
            start_helper = i + 1
            curr_sign = np.sign(grad[i])
    data_list_x.append(x_data[start_helper : len(grad)])
    data_list_y.append(y_data[start_helper : len(grad)])

    return data_list_x, data_list_y


# %%
def hysteresis(dataset, I_threshold=15e-12, parameter_name="lockin_current"):
    data = list(get_parameter_data(dataset=dataset, parameter_name=parameter_name))
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
