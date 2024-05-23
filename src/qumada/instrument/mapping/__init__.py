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
# - Jonas Mertens
# - Sionludi Lab
# - Till Huckeman


from .base import (
    MappingError,
    add_mapping_to_instrument,
    filter_flatten_parameters,
    map_gates_to_instruments,
)
from .mapping_gui import map_terminals_gui


def _build_path(subpath: str) -> str:
    """
    Build the path of the mapping file from this modules directory path and the subdirectory path.

    Args:
        subpath (str): Subpath of the JSON file.

    Returns:
        str: Path to the JSON file.
    """
    return __file__.replace("__init__.py", subpath)


DECADAC_MAPPING = _build_path("Harvard/Decadac.json")
SR830_MAPPING = _build_path("Stanford/SR830.json")
KEITHLEY_2400_MAPPING = _build_path("tektronix/Keithley_2400.json")
KEITHLEY_2450_MAPPING = _build_path("tektronix/Keithley_2450_voltage_source.json")
MFLI_MAPPING = _build_path("Zurich_Instruments/MFLI.json")
QDAC_MAPPING = _build_path("QDevil/QDac.json")
QDAC2_MAPPING = _build_path("QDevil/QDac2.json")
DUMMY_DMM_MAPPING = _build_path("Dummies/DummyDmm.json")
DUMMY_DAC_MAPPING = _build_path("Dummies/DummyDac.json")
DUMMY_CHANNEL_MAPPING = _build_path("Dummies/DummyChannel.json")
KEYSIGHT_B1500_MAPPING = _build_path("Keysight/KeysightB1500.json")

__all__ = [
    "MappingError",
    "add_mapping_to_instrument",
    "map_gates_to_instruments",
    "filter_flatten_parameters",
    "map_terminals_gui",
    "DECADAC_MAPPING",
    "SR830_MAPPING",
    "KEITHLEY_2400_MAPPING",
    "KEITHLEY_2450_MAPPING",
    "MFLI_MAPPING",
    "QDAC_MAPPING",
    "QDAC2_MAPPING",
    "DUMMY_DMM_MAPPING",
    "DUMMY_DAC_MAPPING",
    "KEYSIGHT_B1500_MAPPING"
]
