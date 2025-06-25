import dataclasses
import tempfile
import threading

import numpy as np
import pytest
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





@pytest.fixture
def buffer_settings():
    return {
        "sampling_rate": 512,
        "duration": 12 / 512,
        "burst_duration": 12 / 512,
        "delay": 0,
    }


@pytest.fixture
def parameters():
    return {
        "ohmic": {
            "voltage": {"type": "gettable"},
            "current": {"type": "gettable"},
        },
        "gate1": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 12), "value": 0}},
        "gate2": {"voltage": {"type": "dynamic", "setpoints": np.linspace(0, np.pi, 12), "value": 0}},
    }





def test_1d_buffered(measurement_test_setup, buffer_settings, parameters):
    script = Generic_1D_Sweep_buffered()
    script.setup(
        parameters,
        metadata=None,
        buffer_settings=buffer_settings,
        trigger_type="hardware",
        trigger_start=measurement_test_setup.trigger.set,
        trigger_reset=measurement_test_setup.trigger.clear,
    )

    mapping = {
        "ohmic": {
            "voltage": measurement_test_setup.dmm.voltage,
            "current": measurement_test_setup.dmm.current,
        },
        "gate1": {
            "voltage": measurement_test_setup.dac.ch01.voltage,
        },
        "gate2": {
            "voltage": measurement_test_setup.dac.ch02.voltage,
        },
    }
    script.gate_parameters = mapping
    ds1, ds2 = script.run()
    ds1 = ds1.to_xarray_dataset()
    ds2 = ds2.to_xarray_dataset()

    np.testing.assert_almost_equal(
        parameters["gate1"]["voltage"]["setpoints"],
        ds1.dac_ch01_voltage.values,
    )
    np.testing.assert_almost_equal(
        parameters["gate2"]["voltage"]["setpoints"],
        ds2.dac_ch02_voltage.values,
    )
