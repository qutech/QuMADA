import json

from pytest_httpserver import HTTPServer

from qtools.data.device import Design, Device, Factory, Sample, Wafer
from qtools.data.measurement import (
    Experiment,
    Measurement,
    MeasurementSettings,
    MeasurementSettingScript,
    MeasurementType,
)
from tests.domain_fixtures import *  # pylint: disable=unused-wildcard-import


def ordered(obj):
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


def test_wafer_factory(min_wafer: Wafer, wafer: Wafer):
    new_wafer = Wafer.create("wafer_test", "wafer test description", "20211221")
    assert new_wafer == min_wafer
    new_wafer_2 = Wafer.create(
        name="wafer_test",
        description="wafer test description",
        productionDate="20211221",
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


def test_wafer_save(min_wafer: Wafer, httpserver: HTTPServer):
    # TODO: improve data matching
    data = {
        "name": "wafer_test",
        "description": "wafer test description",
        "productionDate": "20211221",
        "pid": "",
        "creatorId": "",
        "createDate": "",
        "lastChangerId": "",
        "lastChangeDate": "",
    }
    print(data)
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


def test_design_from_pid(json_design, design: Design, httpserver: HTTPServer):
    httpserver.expect_request(
        "/getDesignById",
        query_string="pid=5a89d022-1ffa-4ab5-bd77-cea6b3b95750",
        method="GET",
    ).respond_with_json(json_design)
    assert Design.get_by_id("5a89d022-1ffa-4ab5-bd77-cea6b3b95750") == design


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
    min_design: Design,
    min_sample: Sample,
):
    new_factory = Factory.create("factory_test", "factory test description")
    assert new_factory == min_factory
    new_sample = Sample.create("sample_test", "sample test description", min_wafer)
    assert new_sample == min_sample
    new_design = Design.create(
        "design_test", min_wafer, new_factory, new_sample, "mask", "DG", []
    )
    assert new_design == min_design
    new_device = Device.create("device_test", new_design, new_sample)
    assert new_device == min_device


def test_measurement_factories(
    min_device: Device,
    min_settings: MeasurementSettings,
    min_script: MeasurementSettingScript,
    min_type: MeasurementType,
    min_experiment: Experiment,
    min_measurement: Measurement,
):
    new_script = MeasurementSettingScript.create("script_test", "code", "python", [])
    assert new_script == min_script
    new_settings = MeasurementSettings.create("measurement_settings_test", new_script)
    assert new_settings == min_settings
    new_type = MeasurementType.create(
        name="measurement_type_test",
        model="model",
        scriptTemplate=new_script,
        extractableParameters="X",
        mapping="mapping",
        equipments=[],
    )
    assert new_type == min_type
    new_experiment = Experiment.create(
        name="experiment_test",
        description="experiment test description",
        user="DG",
        group="group",
        measurementType=new_type,
        softwareNoiseFilters=None,
        equipmentInstances=[],
    )
    assert new_experiment == min_experiment
    new_measurement = Measurement.create(
        name="measurement_test",
        device=min_device,
        experiment=new_experiment,
        settings=new_settings,
        measurementParameters="meas_params",
    )
    assert new_measurement == min_measurement
