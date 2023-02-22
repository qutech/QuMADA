from .base import (
    MappingError,
    add_mapping_to_instrument,
    filter_flatten_parameters,
    map_gates_to_instruments,
)


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
DUMMY_DMM_MAPPING = _build_path("Dummies/DummyDmm.json")
DUMMY_DAC_MAPPING = _build_path("Dummies/DummyDac.json")
DUMMY_CHANNEL_MAPPING = _build_path("Dummies/DummyChannel.json")

__all__ = [
    MappingError,
    add_mapping_to_instrument,
    map_gates_to_instruments,
    filter_flatten_parameters,
    DECADAC_MAPPING,
    SR830_MAPPING,
    KEITHLEY_2400_MAPPING,
    KEITHLEY_2450_MAPPING,
    MFLI_MAPPING,
    QDAC_MAPPING,
    DUMMY_DMM_MAPPING,
    DUMMY_DAC_MAPPING,
]
