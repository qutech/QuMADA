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


def get_factories():
    """Gets a list of all factory entries on the db."""
    return _api_get("factories")


def get_wafers():
    """Gets a list of all wafer entries on the db."""
    return _api_get("wafers")


def get_samples():
    """Gets a list of all sample entries on the db."""
    return _api_get("samples")


def get_designs():
    """Gets a list of all design entries on the db."""
    return _api_get("designs")


def get_devices():
    """Gets a list of all device entries on the db."""
    return _api_get("devices")


def get_measurements():
    """Gets a list of all measurement entries on the db."""
    return _api_get("measurements")


def get_measurement_types():
    """Gets a list of all measurement type entries on the db."""
    return _api_get("measurementTypes")


def get_measurement_settings():
    """Gets a list of all measurement setting entries on the db."""
    return _api_get("measurementSettings")


def get_experiments():
    """Gets a list of all experiment entries on the db."""
    return _api_get("experiments")


def get_factory_by_id(pid: str):
    """Get a single factory entry by ID from the db."""
    return _api_get("getFactoryById", {"pid": pid})


def get_wafer_by_id(pid: str):
    """Get a single wafer entry by ID from the db."""
    return _api_get("getWaferById", {"pid": pid})


def get_sample_by_id(pid: str):
    """Get a single sample entry by ID from the db."""
    return _api_get("getSampleById", {"pid": pid})


def get_device_by_id(pid: str):
    """Get a single device entry by ID from the db."""
    return _api_get("getDeviceById", {"pid": pid})


def get_design_by_id(pid: str):
    """Get a single design entry by ID from the db."""
    return _api_get("getDesignById", {"pid": pid})


def get_measurement_by_id(pid: str):
    """Get a single measurement entry by ID from the db."""
    return _api_get("getMeasurementById", {"pid": pid})


def get_measurement_type_by_id(pid: str):
    """Get a single measurement type entry by ID from the db."""
    return _api_get("getMeasurementTypeById", {"pid": pid})


def get_measurement_setting_by_id(pid: str):
    """Get a single measurement setting entry by ID from the db."""
    return _api_get("getMeasurementSettingById", {"pid": pid})


def get_measurement_setting_script_by_id(pid: str):
    """Get a single measurement setting script entry by ID from the db."""
    return _api_get("getMeasurementSettingScriptById", {"pid": pid})


def get_experiment_by_id(pid: str):
    """Get a single experiment entry by ID from the db."""
    return _api_get("getExperimentById", {"pid": pid})


def get_template_parameter_by_id(pid: str):
    """Get a single template parameter entry by ID from the db."""
    return _api_get("getTemplateParameterById", {"pid": pid})


def get_equipment_function_by_id(pid: str):
    """Get a single equipment function entry by ID from the db."""
    return _api_get("getEquipmentFunctionById", {"pid": pid})


def get_equipment_instance_by_id(pid: str):
    """Get a single equipment instance entry by ID from the db."""
    return _api_get("getEquipmentInstanceById", {"pid": pid})


def get_equipment_by_id(pid: str):
    """Get a single equipment entry by ID from the db."""
    return _api_get("getEquipmentById", {"pid": pid})


def save_or_update_factory(description: str,
                           name: str,
                           factory_id: str = None):
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
                         pid: str = None):
    """
    Creates or updates a wafer on the database.

    Args:
        description (str): Description of the wafer
        name (str): Name of the wafer
        productionDate (str): Production date of the wafer
        pid (str, optional): Provide the unique ID of an existing wafer on the database to update it.
                             Defaults to None.
    """
    data = {
        "description": description,
        "name": name,
        "productionDate": production_date
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateWafer", data)


def save_or_update_sample(description: str,
                          name: str,
                          wafer_name: str,
                          pid: str = None):
    """
    Creates or updates a sample on the database.

    Args:
        description (str): Description of the sample
        name (str): Sample name
        wafer_name (str): Wafer name
        pid (str, optional): Provide the unique ID of an existing sample on the database to update it.
                             Defaults to None.
    """
    data = {
        "description": description,
        "name": name,
        "waferName": wafer_name
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateSample", data)


def save_or_update_design(allowed_for_measurement_types: str,
                          creator: str,
                          factory_name: str,
                          mask: str,
                          name: str,
                          sample_name: str,
                          wafer_name: str,
                          pid: str = None):
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
        pid (str, optional): Provide the unique ID of an existing design on the database to update it.
                             Defaults to None.
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
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateDesign", data)


def save_or_update_device(name: str,
                          design_name: str,
                          sample_name: str,
                          pid: str = None):
    """
    Creates or updates a device on the database.

    Args:
        name (str): Device name
        design_name (str): Design name
        sample_name (str): Sample name
        pid (str, optional): Provide the unique ID of an existing device on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "designName": design_name,
        "sampleName": sample_name
    }
    if pid:
        data["pid"] = pid
    return _api_put("saveOrUpdateDevice", data)


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


def save_or_update_template_parameter(name: str,
                                      type: str,
                                      pid: str = None):
    """
    Creates or updates a template parameter on the database.

    Args:
        name (str): Measurement name
        type (str): Type of the template parameter
        pid (str, optional): Provide the unique ID of an existing template parameter on the database to update it.
                             Defaults to None.
    """
    data = {
        "name": name,
        "type": type,
    }
    return _api_put("saveOrUpdateTemplateParameter", data)


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
