#!/usr/bin/env python3

import json
from typing import Any, Dict, Mapping, Set, Iterable, Union

from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.utils.metadata import Metadatable


class MappingError(Exception):
    """Exception is raised, if an error occured during Mapping."""
    ...


def filter_flatten_parameters(node) -> dict[Any, Parameter]:
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

    instrument_parameters: dict[Any, Parameter] = {}
    seen: set[int] = set()
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
    with open(path) as file:
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
    parameters: dict[Any, Parameter] = filter_flatten_parameters(instrument)
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
    parameters: dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapping["parameter_names"] = {key: value.name for key, value in parameters.items()}

    # Dump JSON file
    with open(path, "w") as file:
        json.dump(mapping, file, indent=4, sort_keys=True)


def map_gates_to_instruments(components: Mapping[Any, Metadatable],
                             gate_parameters: Mapping[Any, Union[Mapping[Any, Parameter], Parameter]],
                             existing_gate_parameters: Mapping[Any, Union[Mapping[Any, Parameter], Parameter]] = {}) -> None:
    """
    Maps the gates, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Gates, as defined in the measurement script
        existing_gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]={}): Already existing mapping
                that is used to automatically create the mapping for already known gates without user input.
    """
    # get all parameters in one flat list for the mapping process
    instrument_parameters = filter_flatten_parameters(components)
    for key, gate in gate_parameters.items():
        if isinstance(gate, Parameter):
            # TODO: map single parameter
            # _map_gate_parameters_to_instrument_parameters({key: gate}, )
            ...
        else:
            # map gate to instrument
            # TODO: List is shown even if no user input is required - Fix this
            print(f"Mapping gate {key} to one of the following instruments:")
            for idx, instrument_key in enumerate(components.keys()):
                print(f"{idx}: {instrument_key}")
            chosen = None
            flag = False
            while True:
                try:
                    #Automatically maps all parameters to their corresponding gates
                    #based on the existing mapping
                    for existing_gate, existing_parameters in existing_gate_parameters.items():
                        if existing_gate == key:
                            for channel in existing_parameters.values():
                                if channel:
                                    chosen_instrument = channel.root_instrument
                                    flag = True
                                    print(chosen_instrument)
                                    break   
                                
                    #TODO: Does not work with instruments that have only one parameter
                    #(Lists letters of parametername instead of parameter)
                    if not flag:
                        chosen = int(input(f"Which instrument shall be mapped to gate \"{key}\" ({gate}): "))
                        chosen_instrument = list(components.values())[int(chosen)]
                    chosen_instrument_parameters = {k: v for k, v in instrument_parameters.items() if v.root_instrument is chosen_instrument}
                    try:
                        # Only use chosen instrument's parameters for mapping
                        _map_gate_to_instrument(gate, chosen_instrument_parameters)
                        # Remove mapped parameters from parameter list
                        keys_to_remove = (key for key in chosen_instrument_parameters.keys() if chosen_instrument_parameters[key] in gate.values())
                        for key in keys_to_remove:
                            instrument_parameters.pop(key, None)

                    except MappingError as e:
                        # Could not map instrument, do it manually
                        # TODO: Map to multiple instruments
                        print(e)
                        _map_gate_parameters_to_instrument_parameters(gate, chosen_instrument_parameters)
                        # Remove mapped parameters from parameter list
                        keys_to_remove = (key for key in chosen_instrument_parameters.keys() if chosen_instrument_parameters[key] in gate.values())
                        for key in keys_to_remove:
                            instrument_parameters.pop(key, None)
                    break
                except (IndexError, ValueError):
                    continue
    print("Mapping:" + str(gate_parameters))


def _map_gate_to_instrument(gate: Mapping[Any, Parameter],
                            instrument_parameters: Mapping[Any, Parameter]) -> None:
    """
    Maps the gate parameters of one specific gate to the parameters of one specific instrument.

    Args:
        gate (Mapping[Any, Parameter]): Gate parameters
        instrument_parameters (Mapping[Any, Parameter]): Instrument parameters available for mapping
    """
    mapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")}
    for key, parameter in gate.items():
        # Map only parameters that are not set already
        if parameter is None:
            candidates = [parameter for parameter in mapped_parameters.values() if parameter._mapping == key]
            try:
                gate[key] = candidates.pop(0)
            except IndexError:
                instrument_name = next(iter(instrument_parameters.values())).instrument.name
                raise MappingError(f"No mapping candidate for \"{key}\" in instrument \"{instrument_name}\" found.")


def _map_gate_parameters_to_instrument_parameters(gate_parameters: Mapping[Any, Parameter],
                                                  instrument_parameters: Mapping[Any, Parameter],
                                                  append_unmapped_parameters=True) -> None:
    """
    Maps the gate parameters of one specific gate to the instrument parameters of one specific instrument.

    Args:
        gate_parameters (Mapping[Any, Parameter]): Gate parameters
        instrument_parameters (Mapping[Any, Parameter]): Instrument parameters available for mapping
    """
    mapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")}
    unmapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if not hasattr(parameter, "_mapping")}

    # This is ugly
    for key, parameter in gate_parameters.items():
        if parameter is None:
            # Filter instrument parameters, if _mapping attribute is equal to key_gp
            # if there is no mapping provided, append those parameters to the list
            # if there are no filtered candidates available, show all parameters
            candidates = {k: p for k, p in mapped_parameters.items() if p._mapping == key}
            if append_unmapped_parameters:
                candidates = candidates | unmapped_parameters
            if not len(candidates):
                candidates = mapped_parameters | unmapped_parameters
            candidates_keys = list(candidates.keys())
            candidates_values = list(candidates.values())
            print("Possible instrument parameters:")
            for idx, candidate_key in enumerate(candidates_keys):
                print(f"{idx}: {candidate_key}")
            chosen = None
            while True:
                try:
                    chosen = int(input(f"Please choose an instrument parameter for gate parameter \"{key}\": "))
                    gate_parameters[key] = candidates_values[int(chosen)]
                    break
                except (IndexError, ValueError):
                    continue
