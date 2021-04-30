# -*- coding: utf-8 -*-
'''
Due to problems with the "old" qcodes I decided to get the most basic
measurements running with the latest version, to perform measurements until 
the qtools scripts are working. The measurements routines are not 
yet compatible with the planned qtools-structure (e.g. functions still need 
 instrument parameters rather than gate_mapping object) but can be adapted
later on.
'''
#%%
import os
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
import qcodes as qc
from qcodes import (
    Measurement,
    experiments,
    initialise_database,
    initialise_or_create_database_at,
    load_by_guid,
    load_by_run_spec,
    load_experiment,
    load_last_experiment,
    load_or_create_experiment,
    new_experiment,
)

from qcodes.utils.dataset.doNd import do1d, do2d, plot
from qcodes.dataset.plotting import plot_dataset
from qcodes.logger.logger import start_all_logging
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement

import qtools.utils.browsefiles as bf
import qtools.measurement.gate_mapping as gm

#%%
start_all_logging()
#%% Add imports here

# Only dummy instruments available at home :-(
# A dummy instrument dac with two parameters ch1 and ch2
dac = DummyInstrument('dac', gates=['ch1', 'ch2'])

# A dummy instrument that generates some real looking output depending
# on the values set on the setter_instr, in this case the dac
dmm = DummyInstrumentWithMeasurement('dmm', setter_instr=dac)



station = qc.Station(dac, dmm)

#%% define channels here
sample_name = "dummy_sample"
topgate = keithley
left_barrier = dac.channels[0]
right_barrier = dac.channels[1]
barriers = [left_barrier, right_barrier]
source_drain = lockin



#%%
def set_db_location():
    """
    Used to create or load the sqlite db used to store the measurement results.
    WIP
    Todo:
        - Use QT based filebrowser instead of TKinter one
        - Use filebrowser to specify location for new db  (so far user input 
                                                      in console is necessary)
        - Add exception handling
        - Add the possibility to abort creation
        - Check if database was created successfully
        - Creating a new database causes an exception (although the db is 
                                                       created succesfully)
        - Move to utils?
    """
    load = input("Do you want to load an existing database? [y/n].\n If you choose no, a new one will be created\n")
    if load.lower() == "y":
        initialise_or_create_database_at(bf.browsefiles())#filetypes = (("DB files", "*.db*"))))
        return True
    elif load.lower() == "n":
        path = input("Please enter the directory, where you want to create the DB")
        file = input("Please enter a name for the DB (without suffix)") + ".db"
        initialise_or_create_database_at(path+"\\"+ file)
        return True

    else:
        print("Please enter y or n")
        return set_db_location()
    

#%%

def inducing_measurement(topgate = topgate, barriers = barriers,
                         source_drain = source_drain, topgate_range = [0, 4],
                         datapoints = 1000, delay = 0.01
                         barrier_voltage = 2, source_drain_bias = 1,
                         source_drain_frequency = 173, 
                         experiment_name = "4K_Inducing_measurement",
                         sample = sample_name):
    
    """
    Inducing measurement based on do1d. Writes to database.
    Works only if Keithley2400/2401 is used to control the topgate, DecaDac to
    control the barriers and Stanford Lockin to apply source-drain bias.
    Not yet tested.  
    """
    
    exp = load_or_create_experiment(experiment_name, sample = sample)
    
    for barrier in barriers:
        barrier.ramp(barrier_voltage, 0.3)
    
    topgate.volt.set(0)
    source_drain.amplitude.set(source_drain_bias)
    source_drain.frequency.set(source_drain_frequency)
    
    meas = Measurement(exp = exp, station = station)
    dataset= do1d(topgate.volt, topgate_range[0], topgate_range[1], datapoints, delay,
         tuple(barrier.volt for barrier in barriers), source_drain.R, source_drain.P,
         show_progress=True, do_plot = True)
    
    return dataset

#%%

def pinchoff_measurement_1d(topgate = topgate, barriers = barriers,
                            topgate_volt = 3.5, barrier_voltage = 2,
                            sweep_range = [0,2.5], source_drain = source_drain,
                            source_drain_bias = 1, source_drain_frequency = 173,
                            experiment_name_prefix = "4K_pinchoff_measurement", 
                            sample = sample_name):
    """
    Performs pinchoff measurements for all barriers listed in "barriers" one 
    after another. Same requirements as inducing_measurement()
    Not yet test.
    """
    datasets = []
    for barrier in barriers:
        active_barrier = barrier
        for barrier in barriers:
            if barrier != active_barrier:
                barrier.ramp(barrier_voltage)
            
            experiment_name = experiment_name_prefix + "_" + str(active_barrier)
            exp = load_or_create_experiment(experiment_name, sample = sample)
            
            meas = Measurement(exp = exp, station = station)
            data = do1d(active_barrier.volt, sweep_range[0], sweep_range[1],
                        datapoints, delay, 
                        topgate_volt, tuple(barrier.volt for barrier in barriers),)
                        source_drain.R, source_drain.P, 
                        show_progress = True, do_plot = True)
            datasets.append(data)
    return datasets

        


        
            