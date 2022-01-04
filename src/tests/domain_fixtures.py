import json

import pytest
from pytest_httpserver import HTTPServer

import qtools.data.db as db
from qtools.data.device import Design, Device, Factory, Sample, Wafer
from qtools.data.measurement import (
    Experiment,
    Measurement,
    MeasurementSettings,
    MeasurementSettingScript,
    MeasurementType,
)


@pytest.fixture(scope="function", autouse=True)
def setup_db(httpserver: HTTPServer):
    db.api_url = httpserver.url_for("")


@pytest.fixture(name="min_wafer")
def fixture_min_wafer() -> Wafer:
    return Wafer(
        name="wafer_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description="wafer test description",
        productionDate="20211221",
    )


@pytest.fixture(name="min_factory")
def fixture_min_factory() -> Factory:
    return Factory(
        name="factory_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description="factory test description",
    )


@pytest.fixture(name="min_sample")
def fixture_min_sample(min_wafer: Wafer) -> Sample:
    return Sample(
        name="sample_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description="sample test description",
        wafer=min_wafer,
    )


@pytest.fixture(name="min_design")
def fixture_min_design(
    min_wafer: Wafer, min_factory: Factory, min_sample: Sample
) -> Design:
    return Design(
        name="design_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        wafer=min_wafer,
        factory=min_factory,
        sample=min_sample,
        mask="mask",
        creator="DG",
        allowedForMeasurementTypes=[],
    )


@pytest.fixture(name="device")
def fixture_device(design: Design, sample: Sample) -> Device:
    return Device(
        name="device_test",
        pid="9de71d04-8651-423c-984c-8115d60212ad",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        design=design,
        sample=sample,
    )


@pytest.fixture(name="min_device")
def fixture_min_device(min_design: Design, min_sample: Sample) -> Device:
    return Device(
        name="device_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        design=min_design,
        sample=min_sample,
    )


@pytest.fixture(name="min_script")
def fixture_min_script() -> MeasurementSettingScript:
    return MeasurementSettingScript(
        name="script_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        script="code",
        language="python",
        allowedParameters=[],
    )


@pytest.fixture(name="min_settings")
def fixture_min_settings(min_script: MeasurementSettingScript) -> MeasurementSettings:
    return MeasurementSettings(
        name="measurement_settings_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        script=min_script,
    )


@pytest.fixture(name="min_type")
def fixture_min_type(min_script: MeasurementSettingScript) -> MeasurementType:
    return MeasurementType(
        name="measurement_type_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        model="model",
        scriptTemplate=min_script,
        extractableParameters="X",
        mapping="mapping",
        equipments=[],
    )


@pytest.fixture(name="min_experiment")
def fixture_min_experiment(min_type: MeasurementType) -> Experiment:
    return Experiment(
        name="experiment_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description="experiment test description",
        user="DG",
        group="group",
        measurementType=min_type,
        softwareNoiseFilters=None,
        equipmentInstances=[],
    )


@pytest.fixture(name="min_measurement")
def fixture_min_measurement(
    min_device: Device, min_experiment: Experiment, min_settings: MeasurementSettings
) -> Measurement:
    return Measurement(
        name="measurement_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        device=min_device,
        experiment=min_experiment,
        settings=min_settings,
        measurementParameters="meas_params",
    )


@pytest.fixture(name="wafer")
def fixture_wafer() -> Wafer:
    return Wafer(
        name="wafer_test",
        pid="89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        creatorId="DG",
        createDate="20211220",
        lastChangerId="DG",
        lastChangeDate="20211221",
        description="wafer test description",
        productionDate="20211221",
    )


@pytest.fixture(name="factory")
def fixture_factory() -> Factory:
    return Factory(
        name="factory_test",
        pid="9471ed6c-24ac-443a-b89e-3073ef4cfc52",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        description="factory test description",
    )


@pytest.fixture(name="sample")
def fixture_sample(wafer: Wafer) -> Sample:
    return Sample(
        name="sample_test",
        pid="2afcc0c4-869a-4035-8d41-2d945cd07fb8",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        description="sample test description",
        wafer=wafer,
    )


@pytest.fixture(name="design")
def fixture_design(wafer: Wafer, factory: Factory, sample: Sample) -> Design:
    return Design(
        name="design_test",
        pid="5a89d022-1ffa-4ab5-bd77-cea6b3b95750",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        wafer=wafer,
        factory=factory,
        sample=sample,
        mask="mask",
        creator="DG",
        allowedForMeasurementTypes=[],
    )


@pytest.fixture(name="json_wafer")
def fixture_json_wafer():
    return json.loads(
        """
        {
            "creatorId": "DG",
            "createDate": "20211220",
            "lastChangerId": "DG",
            "lastChangeDate": "20211221",
            "name": "wafer_test",
            "description": "wafer test description",
            "productionDate": "20211221",
            "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
        }
        """
    )


@pytest.fixture(name="json_design")
def fixture_json_design():
    return json.loads(
        """
        {
            "creatorId": "DG",
            "createDate": "20220104",
            "lastChangerId": "DG",
            "lastChangeDate": "20220104",
            "name": "design_test",
            "wafer": {
                "creatorId": "DG",
                "createDate": "20211220",
                "lastChangerId": "DG",
                "lastChangeDate": "20211221",
                "name": "wafer_test",
                "description": "wafer test description",
                "productionDate": "20211221",
                "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
            },
            "factory": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "factory_test",
                "description": "factory test description",
                "pid": "9471ed6c-24ac-443a-b89e-3073ef4cfc52"
            },
            "sample": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "sample_test",
                "description": "sample test description",
                "wafer": {
                    "creatorId": "DG",
                    "createDate": "20211220",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20211221",
                    "name": "wafer_test",
                    "description": "wafer test description",
                    "productionDate": "20211221",
                    "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
                },
                "pid": "2afcc0c4-869a-4035-8d41-2d945cd07fb8"
            },
            "mask": "mask",
            "creator": "DG",
            "allowedForMeasurementTypes": [],
            "pid": "5a89d022-1ffa-4ab5-bd77-cea6b3b95750"
        }
        """
    )


@pytest.fixture(name="json_device")
def fixture_json_device():
    return json.loads(
        """
        {
            "creatorId": "DG",
            "createDate": "20220104",
            "lastChangerId": "DG",
            "lastChangeDate": "20220104",
            "name": "device_test",
            "design": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "design_test",
                "wafer": {
                    "creatorId": "DG",
                    "createDate": "20211220",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20211221",
                    "name": "wafer_test",
                    "description": "wafer test description",
                    "productionDate": "20211221",
                    "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
                },
                "factory": {
                    "creatorId": "DG",
                    "createDate": "20220104",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20220104",
                    "name": "factory_test",
                    "description": "factory test description",
                    "pid": "9471ed6c-24ac-443a-b89e-3073ef4cfc52"
                },
                "sample": {
                    "creatorId": "DG",
                    "createDate": "20220104",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20220104",
                    "name": "sample_test",
                    "description": "sample test description",
                    "wafer": {
                        "creatorId": "DG",
                        "createDate": "20211220",
                        "lastChangerId": "DG",
                        "lastChangeDate": "20211221",
                        "name": "wafer_test",
                        "description": "wafer test description",
                        "productionDate": "20211221",
                        "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
                    },
                    "pid": "2afcc0c4-869a-4035-8d41-2d945cd07fb8"
                },
                "mask": "mask",
                "creator": "DG",
                "allowedForMeasurementTypes": [],
                "pid": "5a89d022-1ffa-4ab5-bd77-cea6b3b95750"
            },
            "sample": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "sample_test",
                "description": "sample test description",
                "wafer": {
                    "creatorId": "DG",
                    "createDate": "20211220",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20211221",
                    "name": "wafer_test",
                    "description": "wafer test description",
                    "productionDate": "20211221",
                    "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
                },
                "pid": "2afcc0c4-869a-4035-8d41-2d945cd07fb8"
            },
            "pid": "9de71d04-8651-423c-984c-8115d60212ad"
        }
        """
    )
