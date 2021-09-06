#!/usr/bin/env python3
"""
Functions and classes regarding the database connection
"""

import json
from typing import Any, Dict, List, Union
import requests


api_url: str = "http://134.61.7.48:9123/{}"


# Return type for API responses
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONType = Union[Dict[str, JSONValue], List[JSONValue]]


def get_factories() -> JSONType:
    response = requests.get(api_url.format("factories"))
    return json.loads(response.content)


def get_factory_by_id(pid: str) -> JSONType:
    response = requests.get(api_url.format("getFactoryById"), {"pid": pid})
    return json.loads(response.content)


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
    response = requests.put(api_url.format("saveOrUpdateFactory"), data=data)
    return json.loads(response.content)


def get_wafers() -> JSONType:
    response = requests.get(api_url.format("wafers"))
    return json.loads(response.content)


def get_wafer_by_id(pid: str) -> JSONType:
    response = requests.get(api_url.format("getWaferById"), {"pid": pid})
    return json.loads(response.content)


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
    response = requests.put(api_url.format("saveOrUpdateWafer"), data=data)
    return json.loads(response.content)


def get_samples() -> JSONType:
    response = requests.get(api_url.format("samples"))
    return json.loads(response.content)


def get_sample_by_id(pid: str) -> JSONType:
    response = requests.get(api_url.format("getSampleById"), {"pid": pid})
    return json.loads(response.content)


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
    response = requests.put(api_url.format("saveOrUpdateSample"), data=data)
    return json.loads(response.content)


def get_designs() -> JSONType:
    response = requests.get(api_url.format("designs"))
    return json.loads(response.content)


def get_design_by_id(pid: str) -> JSONType:
    response = requests.get(api_url.format("getDesignById"), {"pid": pid})
    return json.loads(response.content)


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
    response = requests.put(api_url.format("saveOrUpdateDesign"), data=data)
    return json.loads(response.content)


def get_devices() -> JSONType:
    response = requests.get(api_url.format("devices"))
    return json.loads(response.content)


def get_device_by_id(pid: str) -> JSONType:
    response = requests.get(api_url.format("getDeviceById"), {"pid": pid})
    return json.loads(response.content)


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
    response = requests.put(api_url.format("saveOrUpdateDevice"), data=data)
    return json.loads(response.content)
