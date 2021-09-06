#!/usr/bin/env python3
"""
Functions and classes regarding the database connection
"""

from typing import Any, Dict, List, Union, Mapping
import requests
from urllib.parse import urljoin


# Return type for API responses
JSONValue = Union[str, int, float, bool, None, dict[str, Any], list[Any]]
JSONType = Union[dict[str, JSONValue], list[JSONValue]]


api_url: str = None


def _api_get(function_name: str, params: Mapping = None) -> JSONType:
    """
    Sends a get request to the application server.
    Uses api_url as base url.

    Args:
        function_name (str): API function name
        params (Mapping, optional): Parameters for the API call. Defaults to None.

    Returns:
        JSONType: JSON answer from the application server
    """
    url = urljoin(api_url, function_name)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def _api_put(function_name: str, data: Mapping) -> JSONType:
    """
    Sends a put request to the application server-
    Uses api_url as base url.

    Args:
        function_name (str): API function name
        data (Mapping): Data for the API call

    Returns:
        JSONType: JSON answer from the application server
    """
    url = urljoin(api_url, function_name)
    response = requests.put(url, data=data)
    response.raise_for_status()
    return response.json()


def get_factories():
    return _api_get("factories")


def get_wafers():
    return _api_get("wafers")


def get_samples():
    return _api_get("samples")


def get_designs():
    return _api_get("designs")


def get_devices():
    return _api_get("devices")


def get_measurements():
    return _api_get("measurements")


def get_measurement_types():
    return _api_get("measurementTypes")


def get_measurement_settings():
    return _api_get("measurementSettings")


def get_experiments():
    return _api_get("experiments")


def get_factory_by_id(pid: str):
    return _api_get("getFactoryById", {"pid": pid})


def get_wafer_by_id(pid: str) -> JSONType:
    return _api_get("getWaferById", {"pid": pid})


def get_sample_by_id(pid: str) -> JSONType:
    return _api_get("getSampleById", {"pid": pid})


def get_device_by_id(pid: str) -> JSONType:
    return _api_get("getDeviceById", {"pid": pid})


def get_design_by_id(pid: str) -> JSONType:
    return _api_get("getDesignById", {"pid": pid})


def get_measurement_by_id(pid: str):
    return _api_get("getMeasurementById", {"pid": pid})


def get_measurement_type_by_id(pid: str):
    return _api_get("getMeasurementTypeById", {"pid": pid})


def get_measurement_setting_by_id(pid: str):
    return _api_get("getMeasurementSettingById", {"pid": pid})


def get_experiment_by_id(pid: str):
    return _api_get("getExperimentById", {"pid": pid})


def save_or_update_factory(description: str,
                           name: str,
                           factory_id: str = None) -> JSONType:
    """
    Creates or updates a factory on the database.

    Args:
        description (str): Description of the factory
        name (str): Factory name
    """
    data = {
        "description": description,
        "name": name
    }
    if factory_id:
        data["pid"] = factory_id
    return _api_put("saveOrUpdateFactory", data)


def save_or_update_wafer(description: str,
                         name: str,
                         production_date: str,
                         wafer_id: str = None) -> JSONType:
    """
    Creates or updates a wafer on the database.

    Args:
        description (str): Description of the wafer
        name (str): Name of the wafer
        productionDate (str): Production date of the wafer
        wafer_id (str, optional): Provide the unique ID of an existing wafer on the database to update it. Defaults to None.
    """
    data = {
        "description": description,
        "name": name,
        "productionDate": production_date
    }
    if wafer_id:
        data["pid"] = wafer_id
    return _api_put("saveOrUpdateWafer", data)


def save_or_update_sample(description: str,
                          name: str,
                          wafer_name: str,
                          sample_id: str = None) -> JSONType:
    """
    Creates or updates a sample on the database.

    Args:
        description (str): Description of the sample
        name (str): Sample name
        wafer_name (str): Wafer name
    """
    data = {
        "description": description,
        "name": name,
        "waferName": wafer_name
    }
    if sample_id:
        data["pid"] = sample_id
    return _api_put("saveOrUpdateSample", data)


def save_or_update_design(allowed_for_measurement_types: str,
                          creator: str,
                          factory_name: str,
                          mask: str,
                          name: str,
                          sample_name: str,
                          wafer_name: str,
                          design_id: str = None) -> JSONType:
    """
    Creates or updates an design on the database.

    Args:
        allowed_for_measurement_types (str):
        creator (str): Creator of the design
        factory_name (str): Name of the factory
        mask (str):
        name (str): Design name
        sample_name (str): Sample name
        wafer_name (str): Wafer name
    """
    data = {
        "allowedForMeasumentTypes": allowed_for_measurement_types,
        "creator": creator,
        "factoryName": factory_name,
        "mask": mask,
        "name": name,
        "sampleName": sample_name,
        "waferName": wafer_name
    }
    if design_id:
        data["pid"] = design_id
    return _api_put("saveOrUpdateDesign", data)


def save_or_update_device(name: str,
                          design_name: str,
                          sample_name: str) -> JSONType:
    """
    Creates or updates a device on the database.

    Args:
        name (str): Device name
        design_name (str): Design name
        sample_name (str): Sample name
    """
    data = {
        "name": name,
        "designName": design_name,
        "sampleName": sample_name
    }
    return _api_put("saveOrUpdateDevice", data)


def save_or_update_measurement(name: str,
                               device_name: str,
                               experiment_name: str,
                               measurement_settings_name: str,
                               measurement_parameters) -> JSONType:
    """
    Creates or updates a measurement on the database.

    Args:
        name (str): Measurement name
        device_name (str): Device name
        experiment_name (str): Experiment name
        measurementParameters (str): Measurement parameters
    """
    data = {
        "name": name,
        "deviceName": device_name,
        "experimentName": experiment_name,
        "measurementSettingsName": measurement_settings_name,
        "measurementParameters": measurement_parameters
    }
    return _api_put("saveOrUpdateMeasurement", data)


def save_or_update_measurement_type(name: str,
                                    model: str,
                                    script_template_name: str,
                                    extractable_parameters: str,
                                    mapping: str,
                                    equipment_names: str) -> JSONType:
    """
    Creates or updates a measurement type on the database.

    Args:
        name (str): MeasurementType name
        model (str): Model
        script_template_name (str): MeasurementSettingScript
        extractable_parameters (str): extractable parameters
        mapping (str): Mapping
        equipment_names (str): List of used equipment (comma-separated)
    """
    data = {
        "name": name,
        "model": model,
        "scriptTemplateName": script_template_name,
        "extractableParameters": extractable_parameters,
        "mapping": mapping,
        "equipmentNames": equipment_names
    }
    return _api_put("saveOrUpdateMeasurementType", data)


def save_or_update_experiment(name: str,
                              description: str,
                              user: str,
                              group: str,
                              software_noise_filters: str,
                              measurement_type_name: str,
                              equipment_instance_names: str) -> JSONType:
    """
    Creates or updates an experiment on the database.

    Args:
        name (str): Experiment name
        description (str): Description
        user (str): User
        group (str): Research group of user
        software_noise_filters (str): Used software filters
        measurement_type_name (str): MeasurementType name
        equipment_instance_names (str): List of used equipment instances
    """
    data = {
        "name": name,
        "description": description,
        "user": user,
        "group": group,
        "softwareNoiseFilters": software_noise_filters,
        "measurementTypeName": measurement_type_name,
        "equipmentInstanceNames": equipment_instance_names
    }
    return _api_put("saveOrUpdateExperiment", data)
