# %%
import threading
from collections.abc import Mapping
from time import sleep
from typing import Any

from qcodes.instrument.instrument import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.station import Station
from qcodes.tests.instrument_mocks import DummyChannelInstrument
from qtools_metadata.metadata import Metadata

from qtools.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.mapping import (
    DUMMY_CHANNEL_MAPPING,
    DUMMY_DMM_MAPPING,
    add_mapping_to_instrument,
    filter_flatten_parameters,
    map_terminals_gui,
)
from qtools.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qtools.measurement.scripts.generic_measurement import Generic_1D_Sweep

TerminalParameters = Mapping[Any, Mapping[Any, Parameter] | Parameter]

# Setup qcodes station
station = Station()

# The dummy instruments have a trigger_event attribute as replacement for
# the trigger inputs of real instruments.

dmm = DummyDmm("dmm")
add_mapping_to_instrument(dmm, path=DUMMY_DMM_MAPPING)
print(f"dmm.voltage._mapping: {dmm.voltage._mapping}")
station.add_component(dmm)

dac = DummyDac("dac")
add_mapping_to_instrument(dac, mapping=DummyDacMapping())
print(f"dac.voltage._mapping: {dac.voltage._mapping}")
station.add_component(dac)

# dci = DummyChannelInstrument("dci",channel_names=("ChanA",))
dci = DummyChannelInstrument("dci")
add_mapping_to_instrument(dci, path=DUMMY_CHANNEL_MAPPING)
station.add_component(dci)

parameters: TerminalParameters = {
    "dmm": {"voltage": {"type": "gettable"}, "current": {"type": "gettable"}},
    "dac": {
        "voltage": {
            "type": "dynamic",
            "setpoints": [0, 5],
        }
    },
    "T1": {"temperature": {"type": "gettable"}},
    "T2": {"temperature": {"type": "gettable"}},
}
# parameters: TerminalParameters = {
#     "dmm": {"voltage": {"type": "gettable"}, "current": {"type": "gettable"}},
# }
script = Generic_1D_Sweep()
script.setup(
    parameters,
    None,
    add_script_to_metadata=False,
    add_parameters_to_metadata=False,
)


# %%
from PyQt5.QtWidgets import QApplication

# %%
print(QApplication.instance())

# %%
map_terminals_gui(station.components, script.gate_parameters, monitoring=True)
print("finished")

# %%
map_terminals_gui(station.components, script.gate_parameters, script.gate_parameters, monitoring=True)
print("finished")

# %%
# Testing monitoring (keep_open=True, auto_run=True, monitoring=True)
k = 0
backwards = False
while True:
    sleep(0.01)
    # print("update params")
    dac.set("voltage", k)

    if not backwards:
        if k < 5:
            k = k + 0.1
        else:
            backwards = True
            k = k - 0.1
    else:
        if k > 0:
            k = k - 0.1
        else:
            backwards = False
            k = k + 0.1

# %%
for gate_name, gate in script.gate_parameters.items():
    for param_name, param in gate.items():
        print(gate_name, param_name)
        script.gate_parameters[gate_name][param_name] = None
