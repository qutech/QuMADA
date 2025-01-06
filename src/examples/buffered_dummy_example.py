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
# - Daniel Grothe
# - Till Huckeman

# Ignore flake8 and mypy, as these file is going to be redone either way.
# TODO: Remove these comments then
# flake8: noqa
# type: ignore

# %% Experiment Setup
# As we have only dummy instruments that are not connected, we have to use a global
# trigger event for triggering.
import threading

import numpy as np
import yaml
from qcodes.dataset import (
    Measurement,
    experiments,
    initialise_or_create_database_at,
    load_by_run_spec,
    load_or_create_experiment,
)
from qcodes.station import Station

from qumada.instrument.buffered_instruments import BufferedDummyDMM as DummyDmm
from qumada.instrument.buffers.buffer import (
    load_trigger_mapping,
    map_triggers,
    save_trigger_mapping,
)
from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qumada.instrument.mapping import (
    DUMMY_DMM_MAPPING,
    add_mapping_to_instrument,
    map_terminals_gui,
)
from qumada.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qumada.measurement.scripts import (
    Generic_1D_parallel_asymm_Sweep,
    Generic_1D_parallel_Sweep,
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered,
    Generic_nD_Sweep,
    Timetrace,
)
from qumada.utils.generate_sweeps import generate_sweep, replace_parameter_settings
from qumada.utils.GUI import open_web_gui
from qumada.utils.load_from_sqlite_db import load_db
from qumada.utils.ramp_parameter import *

# %%
trigger = threading.Event()

# Setup qcodes station
station = Station()

# The dummy instruments have a trigger_event attribute as replacement for
# the trigger inputs of real instruments.

dmm = DummyDmm("dmm", trigger_event=trigger)
add_mapping_to_instrument(dmm, mapping=DUMMY_DMM_MAPPING)
station.add_component(dmm)

dac = DummyDac("dac", trigger_event=trigger)
add_mapping_to_instrument(dac, mapping=DummyDacMapping())
station.add_component(dac)

dac2 = DummyDac("dac2", trigger_event=trigger)
add_mapping_to_instrument(dac2, mapping=DummyDacMapping())
station.add_component(dac2)
# %% Load database for data storage
load_db()
# %% Setup measurement
buffer_settings = {
    # "trigger_threshold": 0.005,
    # "trigger_mode": "digital",
    "sampling_rate": 20,
    "duration": 5,
    "burst_duration": 5,
    "delay": 0,
}

# %% Measurement Setup
parameters = {
    "ohmic": {
        "voltage": {"type": "gettable"},
        "current": {"type": "gettable"},
    },
    "gate1": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0}},
    "gate2": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 100), "value": 0}},
}
# %%
script = Generic_1D_Sweep_buffered()
script.setup(
    parameters,
    metadata=None,
    buffer_settings=buffer_settings,
    trigger_type="hardware",
    trigger_start=trigger.set,
    trigger_reset=trigger.clear,
)

map_terminals_gui(station.components, script.terminal_parameters)
map_triggers(station.components)

# %% Run measurement
script.run()
