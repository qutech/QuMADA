# -*- coding: utf-8 -*-
"""
Created on Thu Jan  5 16:04:33 2023

@author: till3
"""

"""
Created on Thu Dec  8 14:36:00 2022

@author: lab2
"""

import qtools_metadata.db as db
import yaml
from qcodes.dataset import (
    Measurement,
    experiments,
    initialise_or_create_database_at,
    load_by_run_spec,
    load_or_create_experiment,
)

from qcodes.station import Station
from qtools_metadata.metadata import Metadata

from qtools.instrument.buffer import map_buffers
from qtools.instrument.buffered_instruments import BufferedDummyDMM as DummyDmm
from qtools.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qtools.instrument.mapping import (
    DUMMY_DMM_MAPPING,
    add_mapping_to_instrument,
)
from qtools.instrument.mapping.base import map_gates_to_instruments
from qtools.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qtools.measurement.scripts import (
    Generic_1D_parallel_asymm_Sweep,
    Generic_1D_parallel_Sweep,
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered,
    Generic_nD_Sweep,
    Timetrace,
)
from qtools.utils.generate_sweeps import generate_sweep, replace_parameter_settings
from qtools.utils.load_from_sqlite_db import load_db, pick_measurement
from qtools.utils.ramp_parameter import *
from qtools.utils.GUI import open_web_gui

#%% Experiment Setup
#As we have only dummy instruments that are not connected, we have to use a global
#trigger event for triggering.
import threading
trigger = threading.Event()

# Setup qcodes station
station = Station()

#The dummy instruments have a trigger_event attribute as replacement for 
#the trigger inputs of real instruments.

dmm = DummyDmm("dmm", trigger_event=trigger)
add_mapping_to_instrument(dmm, path = DUMMY_DMM_MAPPING)
station.add_component(dmm)

dac = DummyDac("dac", trigger_event=trigger)
add_mapping_to_instrument(dac, mapping=DummyDacMapping())
station.add_component(dac)


#%% Metadata Setup
from qtools_metadata.metadata import create_metadata, save_metadata_object_to_db
db.api_url = "http://134.61.7.48:9124"
metadata = create_metadata()

#%% Load database for data storage
load_db()
#%% Setup measurement
buffer_settings = {
    #"trigger_threshold": 0.005,
    #"trigger_mode": "digital",
    "sampling_rate": 10,
    "duration": 5,
    "burst_duration": 5,
    "delay": 0,
}

#%% Measurement Setup
with open(r"C:\Users\till3\Documents\PythonScripts\Test Measurements\testsettings.yaml") as file:
    parameters = yaml.safe_load(file)
#%%
script = Generic_1D_Sweep_buffered()
script.setup(
    parameters,
    metadata,
    buffer_settings=buffer_settings,
    trigger_type="hardware",
    trigger_start= trigger.set, 
    trigger_reset = trigger.clear
)

map_gates_to_instruments(station.components, script.gate_parameters)
map_buffers(station.components, script.properties, script.gate_parameters)

#%% Run measurement
script.run(insert_metadata_into_db=True)
