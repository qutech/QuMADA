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
