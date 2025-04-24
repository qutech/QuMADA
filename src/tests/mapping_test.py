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
# - Daniel Grothe


import json

# pylint: disable=missing-function-docstring
import os
import tempfile
from contextlib import nullcontext as does_not_raise
from datetime import datetime
from random import random

import pytest
from jsonschema import ValidationError
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox
from pytest_cases import fixture_ref, parametrize
from pytest_mock import MockerFixture
from qcodes.instrument_drivers.mock_instruments import (
    DummyChannelInstrument,
    DummyInstrument,
)
from qcodes.station import Station

import qumada.instrument.mapping as mapping
from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qumada.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qumada.instrument.mapping import add_mapping_to_instrument, map_terminals_gui
from qumada.instrument.mapping.base import (
    _load_instrument_mapping,
    load_mapped_terminal_parameters,
    save_mapped_terminal_parameters,
)
from qumada.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qumada.instrument.mapping.mapping_gui import MainWindow
from qumada.measurement.scripts.generic_measurement import Generic_1D_Sweep


@pytest.fixture(name="dmm", scope="session")
def fixture_dmm():
    dmm = DummyDmm("dmm")
    add_mapping_to_instrument(dmm, mapping=mapping.DUMMY_DMM_MAPPING)
    return dmm


@pytest.fixture(name="dac", scope="session")
def fixture_dac():
    dac = DummyDac("dac")
    add_mapping_to_instrument(dac, mapping=DummyDacMapping())
    return dac


@pytest.fixture(name="dci", scope="session")
def fixture_dci():
    dci = DummyChannelInstrument("dci")
    add_mapping_to_instrument(dci, mapping=mapping.DUMMY_CHANNEL_MAPPING)
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


@pytest.fixture(name="unmapped_terminal_parameters")
def fixture_unmapped_terminal_parameters():
    terminal_parameters = {
        "dmm": {"voltage": None, "current": None},
        "dac": {"voltage": None},
        "T1": {"test_parameter": None},
        "T2": {"test_parameter": None},
    }
    return terminal_parameters


# TODO: valid_terminal_parameters_mapping, fixture_script, fixture_station_with_instruments is only valid TOGETHER.
# They must exist within some kind of group
@pytest.fixture(name="mapped_terminal_parameters")
def fixture_mapped_terminal_parameters(station_with_instruments):  # valid for given fixture_station_with_instruments
    terminal_params = {
        "dmm": {"voltage": station_with_instruments.dmm.voltage, "current": station_with_instruments.dmm.current},
        "dac": {"voltage": station_with_instruments.dac.ch01.voltage},
        "T1": {"test_parameter": station_with_instruments.dci.A.temperature},
        "T2": {"test_parameter": station_with_instruments.dci.B.temperature},
    }
    return terminal_params


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


@pytest.fixture
def valid_mapped_terminal_parameter_data():
    data = {
        "dmm": {
            "voltage": "dmm_voltage",
            "current": "dmm_current",
        },
        "dac": {"voltage": "dac_ch01_voltage"},
        "T1": {"test_parameter": "dci_ChanA_temperature"},
        "T2": {"test_parameter": "dci_ChanB_temperature"},
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


def test_save_mapped_terminal_parameters(
    mocker: MockerFixture, mapped_terminal_parameters, valid_mapped_terminal_parameter_data
):
    path = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
    try:
        save_mapped_terminal_parameters(mapped_terminal_parameters, path)
        with open(path) as file:
            contents = json.load(file)
    finally:
        os.remove(path)
    assert valid_mapped_terminal_parameter_data == contents


def test_load_mapped_terminal_parameters(
    mocker: MockerFixture,
    station_with_instruments: Station,
    unmapped_terminal_parameters,
    mapped_terminal_parameters,
    valid_mapped_terminal_parameter_data,
):
    path = "mapped_terminal_parameters.json"
    mock = mocker.mock_open(read_data=json.dumps(valid_mapped_terminal_parameter_data))
    mocker.patch("builtins.open", mock)

    load_mapped_terminal_parameters(
        terminal_parameters=unmapped_terminal_parameters,
        station=station_with_instruments,
        path=path,
    )
    assert mapped_terminal_parameters == unmapped_terminal_parameters


@pytest.mark.parametrize(
    "path",
    [getattr(mapping, name) for name in dir(mapping) if name.endswith("_MAPPING")],
)
def test_validate_mapping_file(path):
    _load_instrument_mapping(path)


def test_instrument_mapping(mocker: MockerFixture, valid_mapping_data):
    instr = DummyInstrument("instrument", ["v1", "v2"])
    mocker_load = mocker.patch(
        "qumada.instrument.mapping.base._load_instrument_mapping",
        return_value=valid_mapping_data,
    )
    path = "pathtomapping.json"

    add_mapping_to_instrument(instr, mapping=path)

    for parameter in [instr.v1, instr.v2]:
        assert parameter._mapping == "voltage"
    mocker_load.assert_called_once_with(path)

    instr.close()


def test_map_terminals_gui(mocker: MockerFixture, station_with_instruments, script):
    mocker.patch("qumada.instrument.mapping.mapping_gui.QApplication", autospec=True)
    mock_main_window = mocker.patch("qumada.instrument.mapping.mapping_gui.MainWindow", autospec=True)

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
def test_mapping_gui_monitoring(monitoring: bool, qtbot, station_with_instruments, script, mocker):
    w = MainWindow(
        station_with_instruments.components,
        script.gate_parameters,
        monitoring=monitoring,
    )
    w.show()

    assert w.monitoring_enable == monitoring
    assert w.terminal_tree.isColumnHidden(2) != monitoring
    # check menu button label
    if not monitoring:
        assert w.toggle_monitoring_action.text() == "Enable"
    else:
        assert w.toggle_monitoring_action.text() == "Disable"

    # trigger toggle_monitoring_action (this is in the menubar)
    w.toggle_monitoring_action.trigger()

    assert w.monitoring_enable != monitoring
    assert w.terminal_tree.isColumnHidden(2) == monitoring
    if monitoring:
        assert w.toggle_monitoring_action.text() == "Enable"
    else:
        assert w.toggle_monitoring_action.text() == "Disable"

    # test monitoring in action (switch back to enabling monitoring first)
    # This block is a bit convoluted because I am actually measuring the value of the monitored param over time
    # in order to test the monitoring
    #   > this is much nicer if I mock the get command (this somehow didnt work for me...)
    if monitoring:
        w.toggle_monitoring_action.trigger()

        # minimal example (dmm.current get command is random number generator)
        w.terminal_parameters["dmm"]["current"] = station_with_instruments.dmm.current

        # update tree to update visuals with manually set mapping
        w.terminal_tree.update_tree()

        QApplication.processEvents()

        # Test setting the monitoring delay
        # mock QInputDialog.getDouble() dialog (for setting a new rate), set a shorter (but random rate)
        delay_seconds = 0.2 + 0.1 * random()
        mocker.patch("qumada.instrument.mapping.mapping_gui.QInputDialog.getDouble", return_value=(delay_seconds, True))
        w.monitoring_refresh_delay.trigger()

        # sample the last get value, wait, sample, wait, sample (catching the change due to get command in monitoring)
        # careful with setting delay_seconds and the actual waiting times.
        # There might be additional delay in process_events function call and cache.get() making this not
        # completely exact. So dont make the window (time margin) too tight.
        before = station_with_instruments.dmm.current.cache.get()
        # wait 0.5*delay_seconds
        # n = 5  # num_steps
        time_now = datetime.now()
        while (datetime.now() - time_now).microseconds < 1e6 * delay_seconds * 0.5:
            pass
        QApplication.processEvents()
        tmp = station_with_instruments.dmm.current.cache.get()

        # wait another 1 delay_seconds
        time_now = datetime.now()
        while (datetime.now() - time_now).microseconds < 1e6 * delay_seconds:
            pass
        QApplication.processEvents()

        after = station_with_instruments.dmm.current.cache.get()

        # this should not have changed yet
        assert before == tmp

        # this makes sure (with high probability) that monitoring called the get function within the second time window
        assert after != before
        # TODO: maybe test this differently. this can fail with some probability...
        # (new random value is equal to old value)


# This somehow doesnt work with the CI/CD pipeline (inside docker container)
# def test_mapping_gui_map_with_enter(mocker, qtbot, station_with_instruments, script):
#     # mock dialogs (specify behaviour in return_value and skip)
#     mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_notallmapped.exec", return_value=QMessageBox.No)
#     mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_duplicates.exec", return_value=QMessageBox.No)
#     mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_overwrite.exec", return_value=QMessageBox.No)

#     w = MainWindow(
#         station_with_instruments.components,
#         script.gate_parameters,
#     )
#     w.show()
#     qtbot.addWidget(w)
#     for _ in range(8):  # 9 is exactly enough to map all terminals
#         qtbot.keyPress(w, Qt.Key_Return)
#         QApplication.processEvents()

#     # wanted mapping
#     # (TODO: better as fixture? Problem is that this has to be manually set and fit to the specific station fixture
#     # (ORDER) and script fixture)
#     terminal_params = {
#         "dmm": {"voltage": station_with_instruments.dmm.voltage, "current": station_with_instruments.dmm.current},
#         "dac": {"voltage": station_with_instruments.dac.voltage},
#         "T1": {"test_parameter": station_with_instruments.dci.A.temperature},
#         "T2": {"test_parameter": station_with_instruments.dci.B.temperature},
#     }

#     # TODO: assert exact mapping that is expected (create fixture for that and assert equality)
#     assert w.terminal_parameters == terminal_params


def test_mapping_gui_map_automatically(mocker, qtbot, station_with_instruments, script):
    # mock dialogs (specify behaviour in return_value and skip)
    mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_notallmapped.exec", return_value=QMessageBox.No)
    mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_duplicates.exec", return_value=QMessageBox.No)
    mocker.patch("qumada.instrument.mapping.mapping_gui.MessageBox_overwrite.exec", return_value=QMessageBox.No)

    w = MainWindow(
        station_with_instruments.components,
        script.gate_parameters,
    )
    w.show()
    qtbot.addWidget(w)

    # wanted mapping
    terminal_params = {
        "dmm": {"voltage": station_with_instruments.dmm.voltage, "current": station_with_instruments.dmm.current},
        "dac": {"voltage": station_with_instruments.dac.ch01.voltage},
        "T1": {"test_parameter": station_with_instruments.dci.A.temperature},
        "T2": {"test_parameter": station_with_instruments.dci.B.temperature},
    }

    # check if auto mapping yields wanted result
    # qtbot.mouseClick(w.button_map_auto, Qt.MouseButton.LeftButton)
    qtbot.keyPress(w, Qt.Key_A)
    assert w.terminal_parameters == terminal_params

    # check if exiting works
    # qtbot.mouseClick(w.button_exit, Qt.MouseButton.LeftButton)
    assert w.isVisible()
    qtbot.keyPress(w, Qt.Key_E)
    assert not w.isVisible()
