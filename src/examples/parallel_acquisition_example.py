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

import threading
from pathlib import Path
import numpy as np


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

map_terminals_gui(station.components, script.gate_parameters)
#map_triggers(station.components) # fails if useing Generic_1D_Sweep()

load_or_create_experiment("test_exp", sample_name="dummy_sample")
# %% Run measurement
script.run()
