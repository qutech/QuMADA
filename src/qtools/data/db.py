#!/usr/bin/env python3
"""
Functions and classes regarding the database connection
"""

from typing import Mapping
from urllib.parse import urljoin

import requests

api_url: str = ""


def _api_get(function_name: str, params: Mapping = None):
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


def _api_put(function_name: str, data: Mapping):
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


def save_or_update_measurement(name: str,
                               device_name: str,
                               experiment_name: str,
                               measurement_settings_name: str,
                               measurement_parameters: str,
                               pid: str = None):
    """
    Creates or updates a measurement on the database.

    Args:
        name (str): Measurement name
        device_name (str): Device name
        experiment_name (str): Experiment name
        measurementParameters (str): Measurement parameters
        pid (str, optional): Provide the unique ID of an existing measurement on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "deviceName": device_name,
        "experimentName": experiment_name,
        "measurementSettingsName": measurement_settings_name,
        "measurementParameters": measurement_parameters
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateMeasurement", data)


def save_or_update_measurement_setting(name: str,
                                       script_id: str,
                                       pid: str = None):
    """
    Creates or updates a measurement setting on the database.

    Args:
        name (str): Measurement name
        script_id (str): pid of the MeasurementSettingScript
        pid (str, optional): Provide the unique ID of an existing measurement setting on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "script_id": script_id,
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateMeasurementSetting", data)


def save_or_update_measurement_setting_script(name: str,
                                              script: str,
                                              language: str,
                                              allowed_parameters: str,
                                              pid: str = None):
    """
    Creates or updates a measurement setting script on the database.

    Args:
        name (str): Measurement name
        script (str): Script content
        language (str): Language of the script
        allowed_parameters (str): comma-separated list of TemplateParameters
        pid (str, optional): Provide the unique ID of an existing measurement setting script on the database
                             to update it. Defaults to None.
    """
    data = {
        "name": name,
        "script": script,
        "language": language,
        "allowedParameters": allowed_parameters,
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateMeasurementSettingScript", data)


def save_or_update_measurement_type(name: str,
                                    model: str,
                                    script_template_name: str,
                                    extractable_parameters: str,
                                    mapping: str,
                                    equipment_names: str,
                                    pid: str = None):
    """
    Creates or updates a measurement type on the database.

    Args:
        name (str): MeasurementType name
        model (str): Model
        script_template_name (str): MeasurementSettingScript
        extractable_parameters (str): extractable parameters
        mapping (str): Mapping
        equipment_names (str): List of used equipment (comma-separated)
        pid (str, optional): Provide the unique ID of an existing measurement type on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "model": model,
        "scriptTemplateName": script_template_name,
        "extractableParameters": extractable_parameters,
        "mapping": mapping,
        "equipmentNames": equipment_names
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateMeasurementType", data)


def save_or_update_experiment(name: str,
                              description: str,
                              user: str,
                              group: str,
                              software_noise_filters: str,
                              measurement_type_id: str,
                              equipment_instance_ids: str,
                              pid: str = None):
    """
    Creates or updates an experiment on the database.

    Args:
        name (str): Experiment name
        description (str): Description
        user (str): User
        group (str): Research group of user
        software_noise_filters (str): Used software filters
        measurement_type_id (str): MeasurementType pid
        equipment_instance_ids (str): List of pid's of used equipment instances
        pid (str, optional): Provide the unique ID of an existing experiment on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "description": description,
        "user": user,
        "group": group,
        "softwareNoiseFilters": software_noise_filters,
        "measurementTypeId": measurement_type_id,
        "equipmentInstanceIds": equipment_instance_ids
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateExperiment", data)


def save_or_update_equipment_instance(name: str,
                                      type: str,
                                      parameter: str,
                                      pid: str = None):
    """
    Creates or updates an equipment instance on the database.

    Args:
        name (str): Equipment instance name
        type (str): Equipment pid
        parameter (str): Parameter of the instance
        pid (str, optional): Provide the unique ID of an existing equipment instance on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "type": type,
        "parameter": parameter,
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateEquipmentInstance", data)


def save_or_update_equipment_function(name: str,
                                      functionType: int,
                                      pid: str = None):
    """
    Creates or updates an equipment function on the database.

    Args:
        name (str): ExperimentFunction name
        functionType (int): FunctionType value
        pid (str, optional): Provide the unique ID of an existing equipment function on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "functionType": functionType,
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateEquipmentFunction", data)


def save_or_update_equipment(name: str,
                             description: str,
                             parameters: str,
                             functions: str,
                             pid: str = None):
    """
    Creates or updates an equipment on the database.

    Args:
        name (str): Equipment name
        description (str): Description
        parameters (str): Parameters of the equipment
        functions (str): Comma-separated list of EquipmentFunction-pid's
        pid (str, optional): Provide the unique ID of an existing equipment on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "type": type,
        "parameters": parameters,
        "functions": functions,
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateEquipment", data)
