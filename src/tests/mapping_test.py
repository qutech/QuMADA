# pylint: disable=missing-function-docstring
import json
from contextlib import nullcontext as does_not_raise

import pytest
from jsonschema import ValidationError
from pytest_cases import fixture_ref, parametrize
from pytest_mock import MockerFixture, mocker
from qcodes.tests.instrument_mocks import DummyInstrument

import qtools.instrument.mapping as mapping
from qtools.instrument.mapping.base import (
    _load_instrument_mapping,
    add_mapping_to_instrument,
)
from qtools.measurement.scripts.generic_measurement import Generic_1D_Sweep


@pytest.fixture
def script():
    return Generic_1D_Sweep()


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


# @pytest.mark.parametrize("instruments")
def test_map_gates_to_instruments():
    ...
