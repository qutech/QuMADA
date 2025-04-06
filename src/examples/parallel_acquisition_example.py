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
# - Hendrik Bluhm

# Ignore flake8 and mypy, as these file is going to be redone either way.
# TODO: Remove these comments then
# flake8: noqa
# type: ignore

# Minimalistic example for locking instruments. Derived from buffered_dummy_example.py

from qcodes import config
from qcodes.station import Station

from qcodes.dataset import (
    #Measurement,
    #experiments,
    initialise_or_create_database_at,
    #load_by_run_spec,
    load_or_create_experiment,
)

from qumada.measurement.scripts import (
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered
)

from qumada.instrument.buffers.buffer import (
    #load_trigger_mapping,
    map_triggers,
    #save_trigger_mapping,
)

from qumada.instrument.mapping import (
    #DUMMY_DMM_MAPPING,
    #add_mapping_to_instrument,
    map_terminals_gui,
)

#from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac, DummyDac_Channel 
from qumada.instrument.custom_drivers.Dummies.dummy_dacLock import DummyDacLock

import qumada.parallelization.workflow as wf

import threading
from pathlib import Path
import numpy as np

config.current_config.dataset.dond_show_progress = True

trigger = threading.Event()

station = Station()
dac = DummyDacLock("dac", trigger_event=trigger)
station.add_component(dac)

initialise_or_create_database_at(Path.home() / "test_db.db")

# %% Measurement Setup
parameters = {
    "ohmic": {
        #"voltage": {"type": "gettable"},
        #"current": {"type": "gettable"},
    },
    "gate1": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0}},
    "gate2": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0}},
#   This does not work (not matching QUMADA conventions)
#    "gate1": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0},
#    "gate2": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0},
}
# %%

#script = Generic_1D_Sweep_buffered()
script = Generic_1D_Sweep()

script.setup(
    parameters,
    metadata=None,
    #buffer_settings=buffer_settings,
    #trigger_type="hardware",
    #trigger_start=trigger.set,
    #trigger_reset=trigger.clear,
)

#
#map_terminals_gui(station.components, script.gate_parameters) # should not be needed for workflows.

#map_triggers(station.components) 
# fails if useing Generic_1D_Sweep() - not good, non-triggered script should still work.
# Call is not script-specific.

load_or_create_experiment("test_exp", sample_name="dummy_sample")
# %% Run measurement

# generate setup map: 1...n -> dummy_dac channels
setup_mappings = [{1: "dac_ch01", 2: "dac_ch02", 3: "dac_ch03", 4: "dac_ch04"}]
# setup_mappings = [{1: "dac_ch01_voltage", 2: "dac_ch02_voltage", 3: "dac_ch03_voltage", 4: "dac_ch04_voltage"}]
# dummy_dac is hardcoded to have four channels, dac_ch0[n], each with parameter voltage.
# parameters in mapping GUI are called dac_ch0[n]_voltage, 
# which is a valid argument to get_component.

# The different qcodes parameters of a single component in general do not necessarily refer to the same output.
# However, quantities like current and voltag can be associated with a single connector.
# A terminal also specifies a physical connection.
# In such cases, it would be natural to map pins to components rather 
# than parameters to make the mapping more general.
# However, this approach needs additional logic for mappings to be fully resolved.
# One would then either have to map identical parametes of a 
# device terminal and a component to each other
# or provide an extra mapping. 
# How do qumada device mappings work?

# The current version causes problem in MeasurementScript.generate_lists: 
# Expects in script.gate_parameters a dictionary for each gate to map all parameters to a channel.

# The natural place to fix this is WorkflowConfiguration.run, 
# where MeasurementScript is already known.
# It suffices to translate only parameters used in measurement_script.

device_mapping = {1: {"gate1": 1, "gate2": 2}, 2: {"gate1": 3, "gate2": 4}}
device_list = [[1], [2]] #optional TODO: allow single indices to be passed.
workflow_config = wf.WorkflowConfiguration(station, setup_mappings, device_mapping)
workflow = wf.Workflow(script)
workflow_config.add_identical_workflows(workflow, device_list)

#script.run()
workflow_config.run()
# Throws "database locked" exception when usinf more than one thread. 
# sqlite3 vonfiguration is threadsafe (sqlite3.threadsafety = 3, serialized, 
# see https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety
# (Checcked in database.py).
# Supposedly happens when transations do not close properly.
# https://www.beekeeperstudio.io/blog/how-to-solve-sqlite-database-is-locked-error
# Setting check_same_thread=False and timeout=20 in database.py->connect() does not
# solve the issue. Did not find other calls of connect().
# Sequential execution of two threads works.
# 0.1 s delay also OK, 20 ms not enoug => Not yet robust
# Also suspect mapping error, adjustment of ramp rate reportted twice for dac_ch03_voltage.

