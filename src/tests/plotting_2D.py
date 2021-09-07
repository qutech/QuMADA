# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 16:45:07 2021

@author: Till Huckemann
"""
import qcodes as qc
import qtools as qt
import qtools.utils.load_from_sqlite_db as ldb
from qtools.utils.browsefiles import browsefiles
from qcodes.dataset.plotting import plot_dataset
from qtools.instrument.mapping.base import flatten_list
import numpy as np
from matplotlib import pyplot as plt
#%%

#R = R_data["lockin_R"]
fig, ax = plt.subplots()

im = plt.pcolormesh(R["dac_Slot1_Chan1_volt"], R["dac_Slot1_Chan2_volt"], grad2, shading = "auto", antialiased = True)
fig.colorbar(im, ax=ax, label = "Conductance (1/$\Omega$)")

#%%
def plot_2D(dataset,
            x_name = "dac_Slot1_Chan1_volt",
            y_name = "dac_Slot1_Chan2_volt",
            z_name = "lockin_R"):
    fig, ax = plt.subplots()
    im = plt.pcolormesh(dataset[x_name], dataset[y_name], dataset[z_name],
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Conductance (1/$\Omega$)")
    plt.show()
    return fig, ax
#%%
def plot_2D_dervative(dataset,
            x_name = "dac_Slot1_Chan1_volt",
            y_name = "dac_Slot1_Chan2_volt",
            z_name = "lockin_R"):
    fig, ax = plt.subplots()
    grad = np.sqrt(np.gradient(dataset[z_name])[0]**2 + np.gradient(dataset[z_name])[1]**2)
    im = plt.pcolormesh(dataset[x_name], dataset[y_name], grad,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Derivative of conductace")
    plt.show()
    return fig, ax

#%%
def plot_2D_sec_dervative(dataset,
            x_name = "dac_Slot1_Chan1_volt",
            y_name = "dac_Slot1_Chan2_volt",
            z_name = "lockin_R"):
    fig, ax = plt.subplots()
    grad = np.gradient(dataset[z_name])
    grad_2= np.sqrt(np.gradient(grad[0])[0]**2+ np.gradient(grad[1])[1]**2 + 2*np.gradient(grad[0])[1]**2)

    im = plt.pcolormesh(dataset[x_name], dataset[y_name], grad_2,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "2nd Derivative of conductace")
    plt.show()
    return fig, ax