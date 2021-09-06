#!/usr/bin/env python3
"""
Functions and classes regarding the database connection
"""

from typing import Any, Dict, List, Union, Mapping
import requests
from urllib.parse import urljoin


# Return type for API responses
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONType = Union[Dict[str, JSONValue], List[JSONValue]]


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
