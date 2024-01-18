# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - 4K User
# - Daniel Grothe
# - Sionludi Lab
# - Till Huckeman


from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any, Union

import jsonschema
from qcodes.instrument import Instrument
from qcodes.metadatable import Metadatable
from qcodes.parameters import Parameter
from qcodes.station import Station

from qumada.metadata import Metadata

logger = logging.getLogger(__name__)


TerminalParameters = Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]


class MappingError(Exception):
    """Exception is raised, if an error occured during Mapping."""


class InstrumentMapping(ABC):
    def __init__(self, mapping_path: str | None, is_triggerable: bool = False):
        if mapping_path:
            self._mapping = _load_instrument_mapping(mapping_path)
        self._is_triggerable = is_triggerable

    @property
    def mapping(self) -> dict:
        return self._mapping

    @abstractmethod
    def ramp(
        self,
        parameters: list[Parameter],
        *,
        start_values: list[float] | None = None,
        end_values: list[float],
        ramp_time: float,
    ) -> None:
        """Wrapper to ramp the provided parameters"""

    @abstractmethod
    def setup_trigger_in(self, trigger_settings: dict) -> None:
        """Setup the trigger based on the buffer_settings"""


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
        except IndexError:
            values = []
        # TODO: Lines 37 and 38 are only a hotfix for problems with the MFLI,
        # The index error is raised somewhere within QCoDeS because the MFLI
        # driver just adds keys that are missing instead of raising the KeyError
        # properly. We should look into this later...
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
    mapping_structure = {
        "type": "object",
        "properties": {
            "parameter_names": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            }
        },
        "required": ["parameter_names"],
    }

    with open(path) as file:
        mapping_data = json.load(file)
    jsonschema.validate(mapping_data, schema=mapping_structure)
    return mapping_data


def add_mapping_to_instrument(
    instrument: Instrument,
    *,
    path: str | None = None,
    mapping: InstrumentMapping | None = None,
) -> None:
    """
    Loads instrument mapping from mapping JSON file and adds it as instrument attribute.
    Alternatively, provide a mapping object, that contains the mapping contents, as well as
    wrapper functions e.g. for ramps

    instr._mapping

    Args:
        instrument (Instrument): Instrument, the mapping is added to.
        path (str): Path to the JSON file.
        mapping (InstrumentMapping): mapping object
    """
    if path is None and mapping is not None:
        helper_mapping = mapping.mapping
        instrument._qumada_ramp = mapping.ramp
        instrument._is_triggerable = mapping._is_triggerable
        instrument._qumada_mapping = mapping
        try:
            instrument._qumada_trigger = mapping.trigger
        except Exception:
            pass
        # TODO: Better name??
    elif path is not None and mapping is None:
        helper_mapping = _load_instrument_mapping(path)
        instrument._is_triggerable = False
    else:
        raise ValueError("Arguments 'path' and 'mapping' are exclusive.")

    mapping = {}
    mapping["parameter_names"] = {
        f"{instrument.name}_{key}": parameter for (key, parameter) in helper_mapping["parameter_names"].items()
    }
    parameters: dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapped_parameters = ((key, parameter) for key, parameter in parameters.items() if key in mapping["parameter_names"])
    for key, parameter in mapped_parameters:
        parameter.__setattr__("_mapping", mapping["parameter_names"][key])


def _generate_mapping_stub(instrument: Instrument, path: str) -> None:
    """
    Generates JSON stub of instrument parametes and saves it under the provided path.
    Overwrites existing files by default.

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
    mapping["parameter_names"] = {
        key.removeprefix(f"{instrument.name}_"): value.name for key, value in parameters.items()
    }

    # Dump JSON file
    with open(path, "w") as file:
        json.dump(mapping, file, indent=4, sort_keys=True)


def map_gates_to_instruments(
    components: Mapping[Any, Metadatable],
    gate_parameters: TerminalParameters,
    existing_gate_parameters: TerminalParameters | None = None,
    *,
    metadata: Metadata | None = None,
    map_manually: bool = False,
) -> None:
    """
    Maps the gates, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        gate_parameters (TerminalParameters): Gates, as defined in the measurement script
        existing_gate_parameters (TerminalParameters | None): Already existing mapping
                that is used to automatically create the mapping for already known gates without user input.
        metadata (Metadata | None): If provided, add mapping to the metadata object.
        map_manually (bool): If set to True, don't try to automatically map parameters to gates. Defaults to False.
    """
    if existing_gate_parameters is None:
        existing_gate_parameters = {}

    # get all parameters in one flat list for the mapping process
    instrument_parameters = filter_flatten_parameters(components)
    # TODO: We have to distinguish multi channel/module instruments. Possible approach:
    #       [parameter]._instrument should be InstrumentChannel or InstrumentModule type
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
                    # Automatically maps all parameters to their corresponding gates
                    # based on the existing mapping
                    for (
                        existing_gate,
                        existing_parameters,
                    ) in existing_gate_parameters.items():
                        if existing_gate == key:
                            if isinstance(existing_parameters, Parameter):
                                # TODO: single parameter
                                ...
                            else:
                                for channel in existing_parameters.values():
                                    if channel:
                                        chosen_instrument = channel.root_instrument
                                        flag = True
                                        print(chosen_instrument)
                                        break

                    # TODO: Does not work with instruments that have only one parameter
                    # (Lists letters of parametername instead of parameter)
                    if not flag:
                        chosen = int(input(f'Which instrument shall be mapped to gate "{key}" ({gate}): '))
                        chosen_instrument = list(components.values())[int(chosen)]
                    chosen_instrument_parameters = {
                        k: v for k, v in instrument_parameters.items() if v.root_instrument is chosen_instrument
                    }
                    try:
                        if map_manually:
                            raise MappingError("map_manually set, mapping manually.")
                        # Only use chosen instrument's parameters for mapping
                        _map_gate_to_instrument(gate, chosen_instrument_parameters)
                        # Remove mapped parameters from parameter list
                        # TODO: remove all parameters from Channel, if parent is a channel
                        keys_to_remove = (
                            key
                            for key in chosen_instrument_parameters.keys()
                            if chosen_instrument_parameters[key] in gate.values()
                        )
                        for key in keys_to_remove:
                            instrument_parameters.pop(key, None)

                    except MappingError as ex:
                        # Could not map instrument, do it manually
                        # TODO: Map to multiple instruments
                        print(ex)
                        _map_gate_parameters_to_instrument_parameters(gate, chosen_instrument_parameters)
                        # Remove mapped parameters from parameter list
                        keys_to_remove = (
                            key
                            for key in chosen_instrument_parameters.keys()
                            if chosen_instrument_parameters[key] in gate.values()
                        )
                        for key in keys_to_remove:
                            instrument_parameters.pop(key, None)
                    break
                except (IndexError, ValueError):
                    continue
    j = json.dumps(gate_parameters, default=lambda o: str(o))
    # Add mapping to metadata, if provided
    if metadata is not None:
        metadata.add_terminal_mapping(json.dumps(j), name="automatic-mapping")


def _map_gate_to_instrument(gate: Mapping[Any, Parameter], instrument_parameters: Mapping[Any, Parameter]) -> None:
    """
    Maps the gate parameters of one specific gate to the parameters of one specific instrument.

    Args:
        gate (Mapping[Any, Parameter]): Gate parameters
        instrument_parameters (Mapping[Any, Parameter]): Instrument parameters available for mapping
    """
    mapped_parameters = {
        key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")
    }
    for key, parameter in gate.items():
        # Map only parameters that are not set already
        if parameter is None:
            candidates = [parameter for parameter in mapped_parameters.values() if parameter._mapping == key]
            try:
                gate[key] = candidates.pop(0)
            except IndexError:
                instrument_name = next(iter(instrument_parameters.values())).instrument.name
                raise MappingError(f'No mapping candidate for "{key}" in instrument "{instrument_name}" found.')


def _map_gate_parameters_to_instrument_parameters(
    gate_parameters: Mapping[Any, Parameter],
    instrument_parameters: Mapping[Any, Parameter],
    append_unmapped_parameters=True,
) -> None:
    """
    Maps the gate parameters of one specific gate to the instrument parameters of one specific instrument.

    Args:
        gate_parameters (Mapping[Any, Parameter]): Gate parameters
        instrument_parameters (Mapping[Any, Parameter]): Instrument parameters available for mapping
    """
    mapped_parameters = {
        key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")
    }
    unmapped_parameters = {
        key: parameter for key, parameter in instrument_parameters.items() if not hasattr(parameter, "_mapping")
    }

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
                    chosen = int(input(f'Please choose an instrument parameter for gate parameter "{key}": '))
                    gate_parameters[key] = candidates_values[int(chosen)]
                    break
                except (IndexError, ValueError):
                    continue


def save_mapped_terminal_parameters(terminal_parameters: TerminalParameters, path: str) -> None:
    """
    Saves already mapped terminals and components to a json file,
    so they can be loaded easily for the exact same setup.

    The saved JSON-structure is as follows:

    {
        "name_of_parameter": {
            "name_of_terminal": "qcodes_parameter_full_name",
            ...
        },
        "name_of_parameter_2": {
            ...
        },
    }
    """
    # Compile concrete mapping data
    tmp_terminal_parameters = {}
    for terminal_parameter, terminals in terminal_parameters.items():
        if isinstance(terminals, Parameter):
            tmp_terminal_parameters[str(terminal_parameter)] = terminals.full_name
        elif isinstance(terminals, MutableMapping):
            terminals_dict = tmp_terminal_parameters[str(terminal_parameter)] = {}
            for terminal, parameter in terminals.items():
                try:
                    terminals_dict[str(terminal)] = parameter.full_name
                except Exception:
                    logger.warning(
                        "Parameter was not saved: Could not get the 'full_name' of parameter %s.", str(parameter)
                    )
    with open(path, mode="w") as file:
        json.dump(tmp_terminal_parameters, file)


def load_mapped_terminal_parameters(terminal_parameters: TerminalParameters, station: Station, path: str) -> None:
    """
    Loads a concrete mapping, that was previously saved to file.
    If errors occur, the mapping will continue, and a warning will
    be logged.

    Warning: Existing mapping for terminal parameters are overwritten if they are given in the file!
    """
    with open(path) as file:
        tmp_terminal_parameters: Mapping[str, Mapping[str, str] | str] = json.load(file)
        assert isinstance(tmp_terminal_parameters, Mapping)

        for parameter_name, terminals in terminal_parameters.items():
            try:
                assert parameter_name in tmp_terminal_parameters
            except AssertionError:
                logger.warning("Parameter could not be loaded: Parameter %s was not found in file.", parameter_name)

            if not isinstance(terminals, MutableMapping):
                # Single parameter, get component by full name
                try:
                    terminal_parameters[parameter_name] = station.get_component(tmp_terminal_parameters[parameter_name])
                except KeyError:
                    logger.warning(
                        "Parameter could not be loaded: QCoDeS station does not contain parameter %s",
                        tmp_terminal_parameters[parameter_name],
                    )
            else:
                # Parameter terminals
                for terminal_name in terminals.keys():
                    try:
                        assert terminal_name in tmp_terminal_parameters[parameter_name]
                    except AssertionError:
                        logger.warning(
                            "Terminal could not be loaded: Terminal %s_%s was not found in file.",
                            parameter_name,
                            terminal_name,
                        )

                    try:
                        terminals[terminal_name] = station.get_component(
                            tmp_terminal_parameters[parameter_name][terminal_name]
                        )
                    except KeyError:
                        logger.warning(
                            "Parameter could not be loaded: QCoDeS station does not contain parameter %s",
                            tmp_terminal_parameters[parameter_name][terminal_name],
                        )
