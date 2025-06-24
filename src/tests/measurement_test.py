import dataclasses
import tempfile

import pytest

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
    Generic_2D_Sweep_buffered,
    Generic_nD_Sweep,
    Timetrace,
)
from qumada.utils.generate_sweeps import generate_sweep, replace_parameter_settings
from qumada.utils.GUI import open_web_gui
from qumada.utils.load_from_sqlite_db import load_db
from qumada.utils.ramp_parameter import *


@dataclasses.dataclass
class MeasurementTestData:
    trigger: threading.Event

    station: Station
    dmm: DummyDmm
    dac: DummyDac


@pytest.fixture
def measurement_test_data():
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


    yield MeasurementTestData(trigger, station, dmm, dac)
    station.close_all_registered_instruments()

@pytest.fixture
def buffer_settings():
    return {
        "sampling_rate": 512,
        "duration": 1e-3,
        "burst_duration": 1e-3,
        "delay": 0,
    }

@pytest.fixture
def parameters():
    return {
        "ohmic": {
            "voltage": {"type": "gettable"},
            "current": {"type": "gettable"},
        },
        "gate1": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 7), "value": 0}},
        "gate2": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 12), "value": 0}},
    }

@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = tmpdir + "test.db"
        load_db(db_path)
        load_or_create_experiment("test", "dummy_sample")
        yield db_path

def test_1d_buffered(measurement_test_data, buffer_settings, parameters, db):
    script = Generic_1D_Sweep_buffered()
    script.setup(
        parameters,
        metadata=None,
        buffer_settings=buffer_settings,
        trigger_type="hardware",
        trigger_start=measurement_test_data.trigger.set,
        trigger_reset=measurement_test_data.trigger.clear,
    )

    mapping = {
        'ohmic': {
                     'voltage': measurement_test_data.dmm.voltage,
                     'current': measurement_test_data.dmm.current,
        },
        'gate1': {'voltage': measurement_test_data.dac.ch01.voltage,},
        'gate2': {'voltage': measurement_test_data.dac.ch01.voltage,},
    }
    script.gate_parameters = mapping
    tmp = script.run()
