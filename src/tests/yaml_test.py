import pytest
from pytest_httpserver import HTTPServer
from yaml.error import YAMLError

from qtools.data.measurement import Measurement
from qtools.data.metadata import Metadata
from tests.domain_fixtures import *  # pylint: disable=unused-wildcard-import


@pytest.fixture(name="metadata")
def fixture_metadata(device: Device, min_measurement: Measurement) -> Metadata:
    min_measurement.device = device
    return Metadata(min_measurement)


@pytest.fixture(name="yaml_metadata")
def fixture_yaml_metadata() -> str:
    return """
        !!python/object:qtools.data.metadata.Metadata
        measurement: !Measurement
            device: !Device "9de71d04-8651-423c-984c-8115d60212ad"
            experiment: !Experiment
                name: experiment_test
                description: experiment test description
                equipmentInstances: []
                group: group
                measurementType: !MeasurementType
                    name: measurement_type_test
                    mapping: mapping
                    model: model
                    extractableParameters: X
                    scriptTemplates:
                    - &id001 !MeasurementSettingScript
                        name: script_test
                        script: code
                        language: python
                        allowedParameters: []
                softwareNoiseFilters: null
                user: DG
            measurementParameters: meas_params
            name: measurement_test
            settings: !MeasurementSettings
                name: measurement_settings_test
                script: *id001
    """


def test_metadata_from_yaml(
    yaml_metadata: str, metadata: Metadata, json_device, httpserver: HTTPServer
):
    httpserver.expect_request(
        "/getDeviceById",
        query_string="pid=9de71d04-8651-423c-984c-8115d60212ad",
        method="GET",
    ).respond_with_json(json_device)

    new_metadata = Metadata.from_yaml(yaml_metadata)
    assert new_metadata == metadata


def test_metadata_from_yaml_wrong_uuid(yaml_metadata: str):
    yaml_metadata = yaml_metadata.replace(
        "9de71d04-8651-423c-984c-8115d60212ad", "9de71d04-8651-423c-984c-8115d60212a"
    )  # removed the last digit
    with pytest.raises(YAMLError):
        Metadata.from_yaml(yaml_metadata)
