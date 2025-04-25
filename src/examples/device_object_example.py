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
# - Till Huckeman

# flake8: noqa: F405

# %% Experiment Setup

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
from qumada.measurement.device_object import *
from qumada.measurement.scripts import (
    Generic_1D_parallel_Sweep,
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered,
    Generic_nD_Sweep,
    Timetrace,
    Timetrace_with_Sweeps_buffered,
)
from qumada.utils.generate_sweeps import generate_sweep
from qumada.utils.load_from_sqlite_db import load_db

# %% Only required to simulate buffered instruments
# As we have only dummy instruments that are not connected, we have to use a global
# trigger event for triggering.
trigger = threading.Event()

# Setup qcodes station and load instruments
station = Station()

# The dummy instruments have a trigger_event attribute as replacement for
# the trigger inputs of real instruments.

# Creating QCoDeS Instrument. For buffered instruments we have to use the QuMada buffered version.
dmm = DummyDmm("dmm", trigger_event=trigger)
# Adding the QuMada mapping
add_mapping_to_instrument(dmm, mapping=DUMMY_DMM_MAPPING)
# Add QCoDes Instrument to station
station.add_component(dmm)

dac1 = DummyDac("dac1", trigger_event=trigger)
add_mapping_to_instrument(dac1, mapping=DummyDacMapping())
station.add_component(dac1)

dac2 = DummyDac("dac2", trigger_event=trigger)
add_mapping_to_instrument(dac2, mapping=DummyDacMapping())
station.add_component(dac2)
# %% Load database for data storage. This will open a window.
# Alternatively, you can use initialise_or_create_database_at from QCoDeS
load_db()
# We need to create an experiment in the QCoDeS database
load_or_create_experiment("test", "dummy_sample")
# %% Setup buffers (only need for buffered measurements).
# Those buffer settings specify how the triggers are setup and how the data is recorded.
buffer_settings = {
    # We don't have to specify threshold and mode for our dummy instruments
    # "trigger_threshold": 0.005,
    # "trigger_mode": "digital",
    "sampling_rate": 20,
    "num_points": 100,
    "delay": 0,
}

# This tells a measurement script how to start a buffered measurement.
# "Hardware" means that you want to use a hardware trigger. To start a measurement,
# the method provided as "trigger_start" is called. The "trigger_reset" method is called
# at the end of each buffered line, in our case resetting the trigger flag.
# For real instruments, you might have to define a method that sets the output of your instrument
# to a desired value as "trigger_start". For details on other ways to setup your triggers,
# check the documentation.

buffer_script_settings = {
    "trigger_type": "hardware",
    "trigger_start": trigger.set,
    "trigger_reset": trigger.clear,
}

# %% Parameters
# This dictionary defines your device. "ohmic", "gate1" and "gate2" are terminals, representing parts of your
# device.
# Each terminal can have multiple parameters that represent values of the terminals
# (here "current" and "voltage"). A real Ohmic connected to a lockin-amplifier could for example have
# additional parameters such as "amplitude" or "frequency". As our dummy_dmm doesn't have those parameters,
# we cannot use them here. Each parameter has to be mapped to a parameter of a QCoDeS instrument later.

parameters = {
    "ohmic": {
        "current": {"type": "gettable"},
    },
    "gate1": {"voltage": {"type": "static"}},
    "gate2": {"voltage": {"type": "static"}},
}

# %% Device
# This creates a device from the dictionary we just specfied.
# device.mapping() will open a GUI that allows you to map the parameters of the device to parameters
# of the measurement instruments (in this case the dummy instruments).
# You can simply use the automated mapping in this case (for details check the documentation).
# Then next two lines save the buffer and trigger settings to the device so we don't have to specify them
# again when we want to run measurements.
# map_triggers will ask you to specify which trigger input to use. Use "software" here.
# You can also load and save parameter
# and trigger mappings to from/to files (see documentation).

device = QumadaDevice.create_from_dict(parameters, station=station, namespace=globals())
device.mapping()
device.buffer_script_setup = buffer_script_settings
device.buffer_settings = buffer_settings
map_triggers(station.components)
# %% Play around

# Change parameter values by calling them
gate2.voltage(0.2)
print(gate2.voltage())

# In case you want to change a voltage parameter, you can also call the terminal directly.
# This works only for getting and setting voltages!
gate1(-0.3)

print(ohmic.current())

# This prints all voltages of the device
device.voltages()

# %% Run simple measurements
# This will ramp gate1 from its current voltage to 0.4 V and record all parameters of type "gettable".
# In this case, this is ohmic.current.

print(ohmic.current.type)
print(gate2.voltage.type)

gate1.voltage.measured_ramp(0.4, buffered=True)

# %% This will also record gate2.voltage. As the dummy dac has no buffer, we cannot record
# a buffered measurement if we want to measure the voltage. The "start" argument can be used to
# start from a different position than the current voltage of gate1. QuMada will by default ramp
# gate1.voltage to the starting point before starting the measurement to avoid artifacts from
# a voltage jump prior to the measurement.
# QuMada measurement scripts will automatically name your measurement unless you explicitely provide
# a name.

gate2.voltage.type = "gettable"
gate1.voltage.measured_ramp(0.4, start=-0.3, name="mymeasurement", buffered=False)  # noqa: F405

gate2.voltage.type = ""  # Don't record it in future measurements.

# %% Save setpoints

print("State 1:")
device.voltages()  # Current state

device.save_state("state1")  # Save current configuration

gate2(0.19)

print("State 2:")
device.voltages()  # New state

device.set_state("state1")  # Reset to stored state
print("Reset to State 1:")
device.voltages()

# %% 2D Scans
# 2D Scans are centered around the current voltage setpoints and return to the
# setpoints are they are done.
# This one will sweep gate1 from 0, to 0.2 V and gate2 from -0.15 to 0.15 V


gate1(0.1)
gate2(0)

print("Before measurement:")
device.voltages()

device.sweep_2D(gate1.voltage, gate2.voltage, 0.2, 0.3, buffered=True)

print("After measurement:")
device.voltages()

# %% Timetraces are recorded at the current setpoint. All measurements return a list of QCoDeS datasets.

data = device.timetrace(duration=10, timestep=0.3, buffered=True)

# If you provide measurement settings such as the timestep or num_points that do not
# match the buffer settings, the buffer settings will be (temporarily) altered to.
# %%
# device.save_to_dict() returns a parameter dictionary based on the current state of the device.

# Alter parameters for measurement...
gate1.voltage.setpoints = np.linspace(0, 0.3, 100)
gate2.voltage.setpoints = np.linspace(0, 0.1, 100)
gate1.voltage.type = "dynamic"
gate2.voltage.type = "dynamic"

print(device.save_to_dict())

# You can feed it back into any measurement script as parameters:
script = Generic_1D_parallel_Sweep()
script.setup(
    device.save_to_dict(),
    metadata=None,
)

# We can provide the mapping from the device object as argument to skip the mapping
map_terminals_gui(station.components, script.gate_parameters, device.instrument_parameters)

script.run()


# %%
# A more convenient way to run arbitrary measurement scripts, is to use
# device.run_measurement, as this uses the advantages of the device.
# Lets for example run a timetrace with sweeps

device.run_measurement(
    script=Timetrace_with_Sweeps_buffered,
    dynamic_params=[gate1.voltage],
    setpoints=[np.linspace(-0.1, 0.1, 100)],
    static_params=[gate2.voltage],
    static_values=[0.3],
    buffered=True,
    name="Timetrace with sweeps",
    duration=20,
)


# The duration is a keyword argument that is passed on to the used measurement
# script.
# It is possible to only provide the script, in this case current settings
# of the device object are used.
