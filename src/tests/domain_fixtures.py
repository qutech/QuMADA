"""Pytest fixtures for database / domain."""

import json
from datetime import datetime

import pytest
from pytest_httpserver import HTTPServer

import qtools.data.db as db
from qtools.data.device import (
    Device,
    DeviceLayout,
    Factory,
    Gate,
    Sample,
    SampleLayout,
    Wafer,
)
from qtools.data.measurement import (
    ExperimentSetup,
    Measurement,
    MeasurementData,
    MeasurementMapping,
    MeasurementScript,
    MeasurementSeries,
    MeasurementSettings,
    MeasurementType,
)


@pytest.fixture(scope="function", autouse=True)
def setup_db(httpserver: HTTPServer):
    """set database url."""
    db.api_url = httpserver.url_for("")


@pytest.fixture(name="min_factory")
def fixture_min_factory() -> Factory:
    """Factory object with minimal input data."""
    return Factory(
        name="factory_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
    )


@pytest.fixture(name="factory")
def fixture_factory() -> Factory:
    """Factory object with more input data."""
    return Factory(
        name="factory_test",
        pid="9471ed6c-24ac-443a-b89e-3073ef4cfc52",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
    )


@pytest.fixture(name="min_wafer")
def fixture_min_wafer(min_factory: Factory) -> Wafer:
    """Wafer object with minimal input data."""
    return Wafer(
        name="wafer_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description=None,
        productionDate="20211221",
        layout=None,
        factory=min_factory,
    )


@pytest.fixture(name="wafer")
def fixture_wafer(factory: Factory) -> Wafer:
    """Wafer object with more input data."""
    return Wafer(
        name="wafer_test",
        pid="89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        creatorId="DG",
        createDate="20211220",
        lastChangerId="DG",
        lastChangeDate="20211221",
        description="wafer test description",
        productionDate="20211221",
        layout="layout",
        factory=factory,
    )


@pytest.fixture(name="json_wafer")
def fixture_json_wafer():
    """JSON answer from application server for Wafer entity."""
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
            "layout": "layout",
            "factory": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "factory_test",
                "pid": "9471ed6c-24ac-443a-b89e-3073ef4cfc52"
            },
            "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
        }
        """
    )


@pytest.fixture(name="min_sample_layout")
def fixture_min_sample_layout() -> SampleLayout:
    """SampleLayout object with minimal input data."""
    return SampleLayout(
        name="sample_layout_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        mask=None,
    )


@pytest.fixture(name="sample_layout")
def fixture_sample_layout() -> SampleLayout:
    """SampleLayout object with more input data."""
    return SampleLayout(
        name="sample_layout_test",
        pid="ceaa9d74-e71e-4b52-bdc2-ddb54863052e",
        creatorId="DG",
        createDate="20220216",
        lastChangerId="DG",
        lastChangeDate="20220216",
        mask="mask",
    )


@pytest.fixture(name="min_sample")
def fixture_min_sample(
    min_wafer: Wafer, min_factory: Factory, min_sample_layout: SampleLayout
) -> Sample:
    """Sample object with minimal input data."""
    return Sample(
        name="sample_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description=None,
        creator=None,
        wafer=min_wafer,
        factory=min_factory,
        layout=min_sample_layout,
    )


@pytest.fixture(name="sample")
def fixture_sample(
    wafer: Wafer, factory: Factory, sample_layout: SampleLayout
) -> Sample:
    """Sample object with more input data."""
    return Sample(
        name="sample_test",
        pid="2afcc0c4-869a-4035-8d41-2d945cd07fb8",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        description="sample test description",
        creator="DG",
        wafer=wafer,
        factory=factory,
        layout=sample_layout,
    )


@pytest.fixture(name="min_gate")
def fixture_min_gate(min_device_layout: DeviceLayout) -> Gate:
    """Gate object with minimal input data."""
    return Gate(
        name="gate_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        function="SD",
        number=None,
        layout=min_device_layout,
    )


@pytest.fixture(name="gate")
def fixture_gate(device_layout: DeviceLayout) -> Gate:
    """Gate object with more input data."""
    return Gate(
        name="gate_test",
        pid="f17a20a3-b857-457b-9a1d-bc970ac9c2f4",
        creatorId="DG",
        createDate="20220216",
        lastChangerId="DG",
        lastChangeDate="20220216",
        function="SD",
        number=0,
        layout=device_layout,
    )


@pytest.fixture(name="min_device_layout")
def fixture_min_device_layout(min_gate: Gate) -> DeviceLayout:
    """DeviceLayout object with minimal input data."""
    return DeviceLayout(
        name="device_layout_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        mask=None,
        image=None,
        creator=None,
        gates=[min_gate],
    )


@pytest.fixture(name="device_layout")
def fixture_device_layout(gate: Gate) -> DeviceLayout:
    """DeviceLayout object with more input data."""
    return DeviceLayout(
        name="device_layout_test",
        pid="5a89d022-1ffa-4ab5-bd77-cea6b3b95750",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        mask="mask",
        image="image",
        creator="DG",
        gates=[gate],
    )


# TODO: How is the recursion done in the json answer?
@pytest.fixture(name="json_device_layout")
def fixture_json_device_layout():
    """JSON answer from application server for DeviceLayout entity."""
    return json.loads(
        """
        {
            "creatorId": "DG",
            "createDate": "20220104",
            "lastChangerId": "DG",
            "lastChangeDate": "20220104",
            "name": "device_layout_test",
            "mask": "mask",
            "image": "image",
            "creator": "DG",
            "gates": [
                {
                    "name": "gate_test",
                    "creatorId": "DG",
                    "createDate": "20220216",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20220216",
                    "function": "SD",
                    "number": 0,
                    "layout": "device_layout",
                    "pid": "f17a20a3-b857-457b-9a1d-bc970ac9c2f4"
                }
            ],
            "pid": "5a89d022-1ffa-4ab5-bd77-cea6b3b95750"
        }
        """
    )


@pytest.fixture(name="min_device")
def fixture_min_device(min_device_layout: DeviceLayout, min_sample: Sample) -> Device:
    """Device object with minimal input data."""
    return Device(
        name="device_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        description=None,
        layoutParameters=None,
        layout=min_device_layout,
        sample=min_sample,
    )


@pytest.fixture(name="device")
def fixture_device(device_layout: DeviceLayout, sample: Sample) -> Device:
    """Device object with full input data."""
    return Device(
        name="device_test",
        pid="9de71d04-8651-423c-984c-8115d60212ad",
        creatorId="DG",
        createDate="20220104",
        lastChangerId="DG",
        lastChangeDate="20220104",
        description="device test description.",
        layoutParameters="a=3,b=4.32",
        layout=device_layout,
        sample=sample,
    )


# TODO: How is the recursion done in the json answer?
@pytest.fixture(name="json_device")
def fixture_json_device():
    """JSON answer from application server for Device entity."""
    return json.loads(
        """
        {
            "creatorId": "DG",
            "createDate": "20220104",
            "lastChangerId": "DG",
            "lastChangeDate": "20220104",
            "name": "device_test",
            "description": "device test description.",
            "layoutParameters": "a=3,b=4.32",
            "layout": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "device_layout_test",
                "mask": "mask",
                "image": "image",
                "creator": "DG",
                "gates": [
                    {
                        "name": "gate_test",
                        "creatorId": "DG",
                        "createDate": "20220216",
                        "lastChangerId": "DG",
                        "lastChangeDate": "20220216",
                        "function": "SD",
                        "number": 0,
                        "layout": device_layout,
                        "pid": "f17a20a3-b857-457b-9a1d-bc970ac9c2f4",
                    }
                ],
                "pid": "5a89d022-1ffa-4ab5-bd77-cea6b3b95750"
            }
            "sample": {
                "creatorId": "DG",
                "createDate": "20220104",
                "lastChangerId": "DG",
                "lastChangeDate": "20220104",
                "name": "sample_test",
                "description": "sample test description",
                "creator": "DG",
                "wafer": {
                    "creatorId": "DG",
                    "createDate": "20211220",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20211221",
                    "name": "wafer_test",
                    "description": "wafer test description",
                    "productionDate": "20211221",
                    "layout": "layout",
                    "factory": {
                        "creatorId": "DG",
                        "createDate": "20220104",
                        "lastChangerId": "DG",
                        "lastChangeDate": "20220104",
                        "name": "factory_test",
                        "pid": "9471ed6c-24ac-443a-b89e-3073ef4cfc52"
                    },
                    "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
                },
                "factory": {
                    "creatorId": "DG",
                    "createDate": "20220104",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20220104",
                    "name": "factory_test",
                    "pid": "9471ed6c-24ac-443a-b89e-3073ef4cfc52"
                },
                "layout": {
                    "name": "sample_layout_test",
                    "creatorId": "DG",
                    "createDate": "20220216",
                    "lastChangerId": "DG",
                    "lastChangeDate": "20220216",
                    "mask": "mask",
                    "pid": "ceaa9d74-e71e-4b52-bdc2-ddb54863052e"
                }
                "pid": "2afcc0c4-869a-4035-8d41-2d945cd07fb8"
            },
            "pid": "9de71d04-8651-423c-984c-8115d60212ad"
        }
        """
    )


@pytest.fixture(name="min_script")
def fixture_min_script() -> MeasurementScript:
    """MeasurementScript object with minimal input data."""
    return MeasurementScript(
        name="script_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        script=None,
        language=None,
    )


@pytest.fixture(name="min_settings")
def fixture_min_settings() -> MeasurementSettings:
    """MeasurementSettings object with minimal input data."""
    return MeasurementSettings(
        name="measurement_settings_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        settings=None,
    )


@pytest.fixture(name="min_mapping")
def fixture_min_mapping() -> MeasurementMapping:
    """MeasurementMapping object with minimal input data."""
    return MeasurementMapping(
        name="measurement_mapping_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        mapping=None,
    )


@pytest.fixture(name="min_series")
def fixture_min_series() -> MeasurementSeries:
    """MeasurementSeries object with minimal input data."""
    return MeasurementSeries(
        name="measurement_series_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        measurements=[],
    )


@pytest.fixture(name="min_type")
def fixture_min_type(min_script: MeasurementScript) -> MeasurementType:
    """MeasurementType with minimal input data."""
    return MeasurementType(
        name="measurement_type_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        extractableParameters="X",
        scriptTemplates=[min_script],
    )


@pytest.fixture(name="min_experiment_setup")
def fixture_min_experiment_setup() -> ExperimentSetup:
    """ExperimentSetup object with minimal input data."""
    return ExperimentSetup(
        name="experiment_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        temperature=None,
        instrumentsChannels=None,
        standardSettings=None,
        filters=None,
    )


@pytest.fixture(name="min_data")
def fixture_min_data() -> MeasurementData:
    """MeasurementData object with minimal input data."""
    return MeasurementData(
        name="measurement_data_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        dataType="hdf5",
        pathToData="/path/to/data.hdf5",
    )


@pytest.fixture(name="min_measurement")
def fixture_min_measurement(
    min_device: Device,
    min_type: MeasurementType,
    min_settings: MeasurementSettings,
    min_mapping: MeasurementMapping,
    min_experiment_setup: ExperimentSetup,
    min_script: MeasurementScript,
    min_series: MeasurementSeries,
    min_data: MeasurementData,
) -> Measurement:
    """Measurement object with minimal input data."""
    return Measurement(
        name="measurement_test",
        pid=None,
        creatorId=None,
        createDate=None,
        lastChangerId=None,
        lastChangeDate=None,
        device=min_device,
        measurementType=min_type,
        settings=min_settings,
        mapping=min_mapping,
        experimentSetup=min_experiment_setup,
        script=min_script,
        series=min_series,
        datetime=datetime(2022, 2, 15, 10, 0, 0),
        user="DG",
        valid=True,
        comments=None,
        data=[min_data],
    )
