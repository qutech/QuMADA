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

from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400


# import src.qtools.utils.browsefiles as bf
# import src.qtools.measurement.gate_mapping as gm

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
#%% Setup all instruments needed
qc.Instrument.close_all()

#dac = Decadac('dac', 'ASRL6::INSTR', default_switch_pos=1) #-1=left, 0=middle, 1=right
dac = Decadac('dac', 'ASRL6::INSTR', min_val=-10, max_val=10,terminator='\n')
lockin=SR830("lockin",'GPIB1::12::INSTR')
keithley=Keithley_2400('keithley', 'GPIB1::26::INSTR')

station = qc.Station(dac, lockin, keithley)
#%% define channels here
sample_name = "AL809789_D2-SD7_QBB36_1_2_SET2"
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
path = r"C:\Users\lab2\data\Huckemann\IMEC\4K_Measurements.db"
initialise_or_create_database_at(path)

#%%

def inducing_measurement(topgate = topgate, left_barrier = left_barrier,
                         right_barrier = right_barrier,
                         source_drain = source_drain, topgate_range = [0, 3.5],
                         datapoints = 250, delay = 0.03,
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
    
    exp = load_or_create_experiment(experiment_name, sample_name = sample)
    
    for barrier in barriers:
        barrier.ramp(barrier_voltage, 0.3)
    
    topgate.volt.set(0)
    source_drain.amplitude.set(source_drain_bias)
    source_drain.frequency.set(source_drain_frequency)
    
    meas = Measurement(exp = exp, station = station)
    
    dataset_up= do1d(topgate.volt, topgate_range[0], topgate_range[1], datapoints, delay,
         left_barrier.volt, right_barrier.volt, source_drain.R, source_drain.P,
         topgate.curr,
         show_progress=True, do_plot = True, measurement_name = "upsweep")
    dataset_down= do1d(topgate.volt, topgate_range[1], topgate_range[0], datapoints, delay,
         left_barrier.volt, right_barrier.volt, source_drain.R, source_drain.P,
         topgate.curr,
         show_progress=True, do_plot = True, measurement_name = "downsweep")
    
    return dataset_up, dataset_down

#%%

def pinchoff_measurement_1d(topgate = topgate, left_barrier = left_barrier,
                            right_barrier = right_barrier,barriers = barriers,
                            topgate_volt = 3, barrier_voltage = 2,
                            datapoints = 500, delay = 0.03,
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
    topgate.volt.set(topgate_volt)
    source_drain.amplitude.set(source_drain_bias)
    #Sweep left barrier
    left_barrier.ramp(0,0.3)
    right_barrier.ramp(2,0.3)
    sleep(5)
    experiment_name = experiment_name_prefix + "_left_barrier"
    exp = load_or_create_experiment(experiment_name, sample_name = sample)
    data = do1d(left_barrier.volt, sweep_range[0], sweep_range[1],
                datapoints, delay, source_drain.R, source_drain.P, right_barrier.volt,
                topgate.volt, topgate.curr,
                show_progress = True, do_plot = True, 
                measurement_name = "upsweep")
    datasets.append(data)
    data = do1d(left_barrier.volt, sweep_range[1], sweep_range[0],
                datapoints, delay, source_drain.R, source_drain.P, right_barrier.volt,
                topgate.volt, topgate.curr,
                show_progress = True, do_plot = True, 
                measurement_name = "downsweep")
    #Sweep right barrier
    right_barrier.ramp(0,0.3)
    left_barrier.ramp(2,0.3)
    sleep(5)
    experiment_name = experiment_name_prefix + "_right_barrier"
    exp = load_or_create_experiment(experiment_name, sample_name = sample)
    data = do1d(right_barrier.volt, sweep_range[0], sweep_range[1],
                datapoints, delay, source_drain.R, source_drain.P, left_barrier.volt,
                topgate.volt, topgate.curr,
                show_progress = True, do_plot = True, 
                measurement_name = "upsweep")
    datasets.append(data)
    data = do1d(right_barrier.volt, sweep_range[1], sweep_range[0],
                datapoints, delay, source_drain.R, source_drain.P, left_barrier.volt,
                topgate.volt, topgate.curr, 
                show_progress = True, do_plot = True, 
                measurement_name = "downsweep")
    
    datasets.append(data)
    return datasets

#%%
def pinchoff_measurement_1d(topgate = topgate, left_barrier = left_barrier,
                            right_barrier = right_barrier,barriers = barriers,
                            topgate_volt = 3, barrier_voltage = 2,
                            datapoints = 500, delay = 0.03,
                            sweep_range = [0,2.5], source_drain = source_drain,
                            source_drain_bias = 1, source_drain_frequency = 173,
                            experiment_name_prefix = "4K_pinchoff_measurement", 
                            sample = sample_name):
    pass