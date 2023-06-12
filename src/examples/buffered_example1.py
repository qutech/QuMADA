# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Till Huckemann
# - Daniel Grothe


import qtools_metadata.db as db
import yaml
from qcodes.dataset import (
    Measurement,
    experiments,
    initialise_or_create_database_at,
    load_by_run_spec,
    load_or_create_experiment,
)
from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
from qcodes.station import Station
from qcodes_contrib_drivers.drivers.QDevil.QDAC1 import QDac
from qtools_metadata.metadata import Metadata

from qtools.instrument.buffered_instruments import BufferedMFLI as MFLI
from qtools.instrument.buffered_instruments import BufferedSR830 as SR830
from qtools.instrument.buffers.buffer import map_buffers
from qtools.instrument.mapping import (
    KEITHLEY_2400_MAPPING,
    MFLI_MAPPING,
    SR830_MAPPING,
    add_mapping_to_instrument,
)
from qtools.instrument.mapping.base import map_gates_to_instruments
from qtools.instrument.mapping.Harvard.Decadac import DecadacMapping
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

#%% Experiment Setup

# Setup qcodes station
station = Station()

# Setup instruments
# Call add_mapping_to_instrument(instrument, mapping) for instruments with built in
# ramp methods or add_mapping_to_instrument(instrument, path) for instruments without
# to map the instrument's parameters to qtools-specific names.

dac = Decadac("dac", "ASRL6::INSTR", min_val=-10, max_val=10, terminator="
")
add_mapping_to_instrument(dac, mapping=DecadacMapping())
station.add_component(dac)

lockin = SR830("lockin", "GPIB1::12::INSTR")
add_mapping_to_instrument(lockin, path=SR830_MAPPING)
station.add_component(lockin)

# keithley = Keithley_2400("keithley", "GPIB1::27::INSTR")
# add_mapping_to_instrument(keithley, path = KEITHLEY_2400_MAPPING)
# station.add_component(keithley)

mfli = MFLI("mfli", "DEV4121", "169.254.40.160")
add_mapping_to_instrument(mfli, path=MFLI_MAPPING)
station.add_component(mfli)

#%% Metadata Setup
from qtools_metadata.metadata import create_metadata, save_metadata_object_to_db

db.api_url = "http://134.61.7.48:9124"
metadata = create_metadata()

#%% Load database for data storage
load_db()
#%% Setup measurement
buffer_settings = {
    # "channel": 0, #?
    "trigger_threshold": 0.005,
    "trigger_mode": "digital",
    "sampling_rate": 512,
    "duration": 1,
    "burst_duration": 1,
    "delay": 0.5,
}
# qdac.ch01.sync_duration(0.2)
# qdac.ch01.sync(1)

#%% Measurement Setup
with open(r"C:\Users\lab2\Documents\DATA\Huckemann\Tests\BufferTest.yaml") as file:
    parameters = yaml.safe_load(file)
#%%
script = Generic_1D_Sweep_buffered()
script.setup(
    parameters,
    metadata,
    buffer_settings=buffer_settings,
    trigger_type="manual",
    sync_trigger=dac.channels[19].volt,
)

map_gates_to_instruments(station.components, script.gate_parameters)
map_buffers(station.components, script.properties, script.gate_parameters)

#%% Run measurement
script.run()
