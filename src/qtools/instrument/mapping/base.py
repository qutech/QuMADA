#!/usr/bin/env python3

import json
from typing import Any, Dict, Set, Iterable

from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.utils.metadata import Metadatable


class MappingError(Exception):
    """Exception is raised, if an error occured during Mapping."""
    ...


def filter_flatten_parameters(node) -> Dict[Any, Parameter]:
    """
    Recursively filters objects of Parameter types from data structure, that consists of dicts, lists and Metadatable.

    Args:
        node (Union[Dict, List, Metadatable]): Current/starting node in the data structure

    Returns:
        Dict[Any, Parameter]: Flat dict of parameters 
    """
    def recurse(node) -> None:
        """Recursive part of the function. Fills instrument_parameters dict."""
        # TODO: Handle InstrumentChannel
        # TODO: Change this try-except-phrase to match-case, when switched to Python3.10
        try:
            values = list(node.values()) if isinstance(node, dict) else list(node)
        except KeyError:
            values = [node]

        for value in values:
            if isinstance(value, Parameter):
                instrument_parameters[value.full_name] = value
            else:
                if isinstance(value, Iterable) and not isinstance(value, str):
                    recurse(value)
                elif isinstance(value, Metadatable):
                    # Object of some Metadatable type, try to get __dict__ and _filter_flatten_parameters
                    try:
                        value_hash = hash(value)
                        if value_hash not in seen:
                            seen.add(value_hash)
                            recurse(vars(value))
                    except TypeError:
                        # End of tree
                        pass

    instrument_parameters: Dict[Any, Parameter] = {}
    seen: Set[int] = set()
    recurse(node)
    return instrument_parameters


def _load_instrument_mapping(path: str) -> Any:
    """
    Loads instrument mapping from mapping JSON file.

    Args:
        path (str): Path to the file.

    Returns:
        Any: Parsed JSON-object
    """
    with open(path, "r") as file:
        return json.load(file)


def add_mapping_to_instrument(instrument: Instrument,
                              path: str) -> None:
    """
    Loads instrument mapping from mapping JSON file and adds it as instrument attribute

    instr._mapping

    Args:
        instrument (Instrument): Instrument, the mapping is added to.
        path (str): Path to the JSON file.
    """
    mapping = _load_instrument_mapping(path)
    parameters: Dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapped_parameters = ((key, parameter) for key, parameter in parameters.items() if key in mapping["parameter_names"])
    for key, parameter in mapped_parameters:
        parameter.__setattr__("_mapping", mapping["parameter_names"][key])


def _generate_mapping_stub(instrument: Instrument,
                          path: str) -> None:
    """
    Generates JSON stub of instrument parametes and saves it under the provided path. Overwrites existing files by default.

    The saved JSON-structure is as follows:

    {
        "parameter_names": {
            "instrument_par1": par1,
            "instrument_par2": par2,
            "instrument_par3": par3,
            ...
        }
    }

    After generating the stub, it can be edited, to map different parameter names to the instrument parameters.

    Args:
        instrument (Instrument): Instrument, that shall be parsed
        path (str): Save path for the JSON file
    """
    # Create mapping stub from flat dict of parameters
    mapping = {}
    parameters: Dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapping["parameter_names"] = {key: value.name for key, value in parameters.items()}

    # Dump JSON file
    with open(path, "w") as file:
        json.dump(mapping, file, indent=4, sort_keys=True)
