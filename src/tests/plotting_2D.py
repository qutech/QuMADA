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
#from qtools.instrument.mapping.base import flatten_list
import numpy as np
from matplotlib import pyplot as plt

#%%

#R = R_data["lockin_R"]
# fig, ax = plt.subplots()

# im = plt.pcolormesh(R["dac_Slot1_Chan1_volt"], R["dac_Slot1_Chan2_volt"], grad2, shading = "auto", antialiased = True)
# fig.colorbar(im, ax=ax, label = "Conductance (1/$\Omega$)")
#How to get data:
# data = ldb.list_measurements_for_sample()
# dataset= data[94]
# dataset = dataset.get_parameter_data()["lockin_current"]
#%%
def plot_2D(dataset,
            x_name = "dac_Slot0_Chan1_volt",
            y_name = "dac_Slot0_Chan2_volt",
            z_name = "lockin_current"):
    fig, ax = plt.subplots(figsize = (20,10))
    x_data = rearrange_data(dataset, z_name, x_name)
    y_data = rearrange_data(dataset, z_name, y_name)
    z_data = rearrange_data(dataset, z_name, z_name)
    print(x_data)
    print(y_data)
    print(z_data)
    im = plt.pcolormesh(x_data, y_data, z_data,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Conductance (1/$\Omega$)")
    plt.show()
    return fig, ax

#%%
def plot_2D_old(dataset,
            x_name = "dac_Slot0_Chan1_volt",
            y_name = "dac_Slot0_Chan2_volt",
            z_name = "lockin_current"):
    fig, ax = plt.subplots( )
    im = plt.pcolormesh(dataset[x_name], dataset[y_name], dataset[z_name],
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Conductance (1/$\Omega$)")
    plt.show()
    return fig, ax
#%%
def oldplot_2D_derivative(dataset,
            x_name = "dac_Slot0_Chan1_volt",
            y_name = "dac_Slot0_Chan2_volt",
            z_name = "lockin_current"):
    fig, ax = plt.subplots()
    x_data = rearrange_data(dataset, z_name, x_name)
    y_data = rearrange_data(dataset, z_name, y_name)
    z_data = rearrange_data(dataset, z_name, z_name)
    grad = np.sqrt(np.gradient(dataset[z_name])[0]**2 + np.gradient(dataset[z_name])[1]**2)
    im = plt.pcolormesh(dataset[x_name], dataset[y_name], grad,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Derivative of conductace")
    plt.show()
    return fig, ax

#%%
def plot_2D_derivative(dataset,
            x_name = "dac_Slot0_Chan1_volt",
            y_name = "dac_Slot0_Chan2_volt",
            z_name = "lockin_current"):
    fig, ax = plt.subplots()
    x_data = rearrange_data(dataset, z_name, x_name)
    y_data = rearrange_data(dataset, z_name, y_name)
    z_data = rearrange_data(dataset, z_name, z_name)
    grad = np.sqrt(np.gradient(z_data)[0]**2 + np.gradient(z_data)[1]**2)
    im = plt.pcolormesh(x_data[0,:], y_data[:,0], grad,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "Derivative of conductace")
    plt.show()
    return fig, ax


#%%
def plot_2D_sec_dervative(dataset,
            x_name = "dac_Slot1_Chan2_volt",
            y_name = "dac_Slot2_Chan0_volt",
            z_name = "lockin_current"):
    fig, ax = plt.subplots()
    grad = np.gradient(dataset[z_name])
    grad_2= np.sqrt(np.gradient(grad[0])[0]**2+ np.gradient(grad[1])[1]**2 + 2*np.gradient(grad[0])[1]**2)

    im = plt.pcolormesh(dataset[x_name], dataset[y_name], grad_2,
                        shading = "auto", antialiased=True)
    fig.colorbar(im, ax = ax, label = "2nd Derivative of conductace")
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
#def list_channels(dataset):
    
#%%

def rearrange_data(dataset, subset = "lockin_current", parameter_name = "lockin_current"):
    shape = dataset.description.shapes[subset]
    data = dataset.get_parameter_data()[subset][parameter_name]
    n=0
    print(data.shape)
    print(shape)
    if list(data.shape) == shape:
        print("alright")
        
        return data
    else:
        data_array = np.zeros(shape)
        print(data_array.shape)
        for i in range(0, shape[1]):
            for j in range(0,shape[0]):
                try:
                    data_array[i,j] = data[i*shape[0]+j]
                except: 
                    data_array = data_array[i-1,:]
                    break
                break
                    # try:
                    #     data_array[i,j] = 0
                    # except IndexError:
                        
                n+=1
        #print(data_array)
        return data_array

ldb.load_db()
broken_data =ldb.pick_measurement()
plot_2D(broken_data)    
    