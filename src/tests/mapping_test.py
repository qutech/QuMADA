# pylint: disable=missing-function-docstring
import json
from contextlib import nullcontext as does_not_raise

import pytest
from jsonschema import ValidationError
from PyQt5.QtCore import Qt
from pytest_cases import fixture_ref, parametrize
from pytest_mock import MockerFixture
from qcodes.station import Station
from qcodes.tests.instrument_mocks import DummyChannelInstrument, DummyInstrument

import qtools.instrument.mapping as mapping
from qtools.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.mapping import add_mapping_to_instrument, map_terminals_gui
from qtools.instrument.mapping.base import _load_instrument_mapping
from qtools.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qtools.instrument.mapping.mapping_gui import MainWindow
from qtools.measurement.scripts.generic_measurement import Generic_1D_Sweep


@pytest.fixture(name="dmm", scope="session")
def fixture_dmm():
    dmm = DummyDmm("dmm")
    add_mapping_to_instrument(dmm, path=mapping.DUMMY_DMM_MAPPING)
    return dmm


@pytest.fixture(name="dac", scope="session")
def fixture_dac():
    dac = DummyDac("dac")
    add_mapping_to_instrument(dac, mapping=DummyDacMapping())
    return dac


@pytest.fixture(name="dci", scope="session")
def fixture_dci():
    dci = DummyChannelInstrument("dci")
    add_mapping_to_instrument(dci, path=mapping.DUMMY_CHANNEL_MAPPING)
    return dci


@pytest.fixture(name="station_with_instruments", scope="session")
def fixture_station_with_instruments(dmm, dac, dci):
    station = Station()
    station.add_component(dmm)
    station.add_component(dac)
    station.add_component(dci)
    return station


@pytest.fixture(name="script")
def fixture_script():
    parameters = {
        "dmm": {"voltage": {"type": "gettable"}, "current": {"type": "gettable"}},
        "dac": {
            "voltage": {
                "type": "dynamic",
                "setpoints": [0, 5],
            }
        },
        "T1": {"test_parameter": {"type": "gettable"}},
        "T2": {"test_parameter": {"type": "gettable"}},
    }
    script = Generic_1D_Sweep()
    script.setup(
        parameters=parameters,
        metadata=None,
        add_script_to_metadata=False,
        add_parameters_to_metadata=False,
    )
    return script


@pytest.fixture
def valid_mapping_data():
    data = {
        "parameter_names": {
            "IDN": "IDN",
            "v1": "voltage",
            "v2": "voltage",
        }
    }
    return data


@pytest.fixture
def invalid_mapping_data():
    data = {
        "parameters": {
            "IDN": "IDN",
            "v1": "voltage",
            "v2": "voltage",
        }
    }
    return data


@parametrize(
    "mapping_data, expectation",
    [
        (fixture_ref(valid_mapping_data), does_not_raise()),
        (fixture_ref(invalid_mapping_data), pytest.raises(ValidationError)),
    ],
)
def test_load_instrument_mapping(mocker: MockerFixture, mapping_data, expectation):
    with expectation:
        path = "pathtomapping.json"
        mock = mocker.mock_open(read_data=json.dumps(mapping_data))
        mocker.patch("builtins.open", mock)

        ret = _load_instrument_mapping(path)
        assert ret == mapping_data
        mock.assert_called_once_with(path)


@pytest.mark.parametrize(
    "path",
    [getattr(mapping, name) for name in dir(mapping) if name.endswith("_MAPPING")],
)
def test_validate_mapping_file(path):
    _load_instrument_mapping(path)


def test_instrument_mapping(mocker: MockerFixture, valid_mapping_data):
    instr = DummyInstrument("instrument", ["v1", "v2"])
    mocker_load = mocker.patch(
        "qtools.instrument.mapping.base._load_instrument_mapping",
        return_value=valid_mapping_data,
    )
    path = "pathtomapping.json"

    add_mapping_to_instrument(instr, path=path)

    for parameter in [instr.v1, instr.v2]:
        assert parameter._mapping == "voltage"
    mocker_load.assert_called_once_with(path)

    instr.close()


def test_map_terminals_gui(mocker: MockerFixture, station_with_instruments, script):
    mocker.patch("qtools.instrument.mapping.mapping_gui.QApplication", autospec=True)
    mock_main_window = mocker.patch("qtools.instrument.mapping.mapping_gui.MainWindow", autospec=True)

    kwargs = {
        "components": station_with_instruments.components,
        "terminal_parameters": script.gate_parameters,
        "monitoring": False,
    }
    map_terminals_gui(**kwargs)
    main_window_instance = mock_main_window.return_value

    mock_main_window.assert_called_once_with(**kwargs)
    main_window_instance.show.assert_called_once()


@pytest.mark.parametrize("monitoring", [True, False])
def test_mapping_gui(monitoring: bool, qtbot, station_with_instruments, script):
    w = MainWindow(
        station_with_instruments.components,
        script.gate_parameters,
        monitoring=monitoring,
    )
    w.show()
    qtbot.addWidget(w)
    qtbot.mouseClick(w.button_map_auto, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(w.button_exit, Qt.MouseButton.LeftButton)
