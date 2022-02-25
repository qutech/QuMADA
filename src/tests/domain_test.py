# pylint: disable=missing-function-docstring
import json
from cmath import exp

from pytest_httpserver import HTTPServer

from qtools.data.device import Device, DeviceLayout, Factory, Sample, Wafer
from qtools.data.measurement import (
    ExperimentSetup,
    Measurement,
    MeasurementScript,
    MeasurementSettings,
    MeasurementType,
)
from tests.domain_fixtures import *  # pylint: disable=unused-wildcard-import


def ordered(obj):
    """Order both list and dict. Return every other"""
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


def test_wafer_from_json(json_wafer, wafer: Wafer):
    new_wafer = Wafer(**json_wafer)
    assert new_wafer == wafer
    new_wafer.name = "not_test"
    assert new_wafer != wafer


def test_wafer_to_json(json_wafer, wafer: Wafer):
    assert ordered(json_wafer) == ordered(json.loads(wafer.to_json()))
    wafer.name = "not_test"
    assert ordered(json_wafer) != ordered(json.loads(wafer.to_json()))


def test_wafer_factory(
    min_wafer: Wafer, wafer: Wafer, min_factory: Factory, factory: Factory
):
    new_wafer = Wafer.create("wafer_test", "20211221", min_factory)
    assert new_wafer == min_wafer
    new_wafer_2 = Wafer.create(
        name="wafer_test",
        description="wafer test description",
        productionDate="20211221",
        factory=factory,
        layout="layout",
        pid="89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        creatorId="DG",
        createDate="20211220",
        lastChangerId="DG",
        lastChangeDate="20211221",
    )
    assert new_wafer_2 == wafer


def test_wafer_from_pid(json_wafer, wafer: Wafer, httpserver: HTTPServer):
    httpserver.expect_request(
        "/getWaferById",
        query_string="pid=89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        method="GET",
    ).respond_with_json(json_wafer)
    assert Wafer.get_by_id("89738c4a-e46b-40de-b2fd-c5aaeea7175c") == wafer


def test_wafer_get_all(json_wafer, wafer: Wafer, httpserver: HTTPServer):
    httpserver.expect_request("/wafers").respond_with_json([json_wafer, json_wafer])
    wafers = Wafer.get_all()
    assert wafers == [wafer, wafer]


def test_wafer_save(min_wafer: Wafer, min_factory: Factory, httpserver: HTTPServer):
    # TODO: improve data matching
    data = {
        "name": "wafer_test",
        "description": "",
        "productionDate": "20211221",
        "factory": min_factory,
        "pid": "",
        "creatorId": "",
        "createDate": "",
        "lastChangerId": "",
        "lastChangeDate": "",
    }
    response = {
        "status": True,
        "id": "89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        "errorMessage": None,
    }
    httpserver.expect_request(
        "/saveOrUpdateWafer", method="PUT", json=data
    ).respond_with_json(response)
    assert min_wafer.save() == "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
    assert min_wafer.pid == "89738c4a-e46b-40de-b2fd-c5aaeea7175c"


def test_device_layout_from_pid(
    json_device_layout, device_layout: DeviceLayout, httpserver: HTTPServer
):
    httpserver.expect_request(
        "/getDesignById",
        query_string="pid=5a89d022-1ffa-4ab5-bd77-cea6b3b95750",
        method="GET",
    ).respond_with_json(json_device_layout)
    assert (
        DeviceLayout.get_by_id("5a89d022-1ffa-4ab5-bd77-cea6b3b95750") == device_layout
    )


def test_device_from_pid(json_device, device: Device, httpserver: HTTPServer):
    httpserver.expect_request(
        "/getDeviceById",
        query_string="pid=9de71d04-8651-423c-984c-8115d60212ad",
        method="GET",
    ).respond_with_json(json_device)
    assert Device.get_by_id("9de71d04-8651-423c-984c-8115d60212ad") == device


def test_device_factories(
    min_factory: Factory,
    min_wafer: Wafer,
    min_device: Device,
    min_device_layout: DeviceLayout,
    min_gate: Gate,
    min_sample: Sample,
):
    new_factory = Factory.create("factory_test")
    assert new_factory == min_factory
    new_sample = Sample.create("sample_test", min_wafer, min_factory, min_device_layout)
    assert new_sample == min_sample
    new_gate = Gate.create("gate_test", "SD", layout=min_device_layout)
    assert new_gate == min_gate
    new_device_layout = DeviceLayout.create("design_test", gates=[min_gate])
    assert new_device_layout == min_device_layout
    new_device = Device.create("device_test", new_device_layout, new_sample)
    assert new_device == min_device


def test_measurement_factories(
    min_device: Device,
    min_settings: MeasurementSettings,
    min_mapping: MeasurementMapping,
    min_script: MeasurementScript,
    min_type: MeasurementType,
    min_experiment_setup: ExperimentSetup,
    min_series: MeasurementSeries,
    min_data: MeasurementData,
    min_measurement: Measurement,
):
    new_script = MeasurementScript.create("script_test")
    assert new_script == min_script
    new_settings = MeasurementSettings.create("measurement_settings_test")
    assert new_settings == min_settings
    new_mapping = MeasurementMapping.create("measurement_mapping_test")
    assert new_mapping == min_mapping
    new_type = MeasurementType.create(
        name="measurement_type_test",
        extractableParameters="X",
        scriptTemplates=[new_script],
    )
    assert new_type == min_type
    new_experiment_setup = ExperimentSetup.create(name="experiment_test")
    assert new_experiment_setup == min_experiment_setup
    new_series = MeasurementSeries.create("measurement_series_test")
    assert new_series == min_series
    new_data = MeasurementData.create(
        "measurement_data_test", "hdf5", "/path/to/data.hdf5"
    )
    assert new_data == min_data
    new_measurement = Measurement.create(
        name="measurement_test",
        device=min_device,
        measurementType=new_type,
        settings=new_settings,
        mapping=new_mapping,
        experimentSetup=new_experiment_setup,
        script=new_script,
        series=new_series,
        datetime=datetime(2022, 2, 15, 10, 0, 0),
        user="DG",
        valid=True,
        data=[new_data],
    )
    assert new_measurement == min_measurement
