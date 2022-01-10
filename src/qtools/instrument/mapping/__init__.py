def _build_path(subpath: str) -> str:
    """
    Build the path of the mapping file from this modules directory path and the subdirectory path.

    Args:
        subpath (str): Subpath of the JSON file.

    Returns:
        str: Path to the JSON file.
    """
    return __file__.replace("__init__.py", subpath)


DECADAC_MAPPING = _build_path("Decadac.json")
SR830_MAPPING = _build_path("lockin.json")
KEITHLEY_2400_MAPPING = _build_path("tektronix/Keithley_2400.json")
KEITHLEY_2450_MAPPING = _build_path("tektronix/Keithley_2450_voltage_source.json")
MFLI_MAPPING = _build_path("Zurich_Instruments/MFLI.json")
