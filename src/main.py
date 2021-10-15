#!/usr/bin/env python3
import argparse
from typing import Any, MutableMapping

import qcodes as qc
import qcodes.instrument.sims as qcsims
from qcodes.instrument.base import Instrument
from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.tests.instrument_mocks import (
    DummyInstrument,
    DummyInstrumentWithMeasurement,
)

import qtools.data.db as db
# Filenames for simulation files
import qtools.instrument.sims as qtsims
from qtools.data.base import create_metadata_device
from qtools.data.metadata import Metadata
from qtools.instrument.mapping.base import (
    add_mapping_to_instrument,
    filter_flatten_parameters,
    map_gates_to_instruments,
)
from qtools.measurement.measurement import QtoolsStation as Station
from qtools.measurement.measurement_for_immediate_use.generic_measurement import (
    Generic_1D_Sweep,
    Generic_nD_Sweep,
)
from qtools.measurement.measurement_for_immediate_use.inducing_measurement import (
    InducingMeasurementScript,
)

DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
KEITHLEY_2450_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')

# Filenames for mapping files
from qtools.instrument.mapping import (
    DECADAC_MAPPING,
    KEITHLEY_2400_MAPPING,
    KEITHLEY_2450_MAPPING,
    SR830_MAPPING,
)


def _initialize_instruments() -> MutableMapping[Any, Instrument]:
    """
    Initializes the instruments as qcodes components.

    Returns:
        MutableMapping[Any, EquipmentInstance]: Instruments, that can be loaded into qcodes Station.#
    """
    qc.Instrument.close_all() # Remove all previous initialized instruments

    # TODO: Maybe do this in UI
    instruments: dict[str, Instrument] = {}

    # Initialize instruments for simulation
    dac = instruments["dac"] = DummyInstrument("dac", ("voltage1", "voltage2"))
    instruments["dmm"] = DummyInstrumentWithMeasurement("dmm", dac)

    lockin = instruments["lockin"] = DummyInstrument("lockin", ("amplitude", "frequency", "current"))
    instruments["dmm2"] = DummyInstrumentWithMeasurement("dmm2", lockin)

    keithley = instruments["keithley"] = Keithley2450("keithley", "GPIB::2::INSTR", visalib=KEITHLEY_2450_VISALIB)
    add_mapping_to_instrument(keithley, KEITHLEY_2450_MAPPING)

    # initialize real instruments
    # dac = instruments["dac"] = Decadac("dac",
    #                                     "ASRL6::INSTR",
    #                                     min_val=-10, max_val=10,
    #                                     terminator="\n")
    # add_mapping_to_instrument(dac, DECADAC_MAPPING)

    # lockin = instruments["lockin"] = SR830("lockin", "GPIB1::12::INSTR")
    # add_mapping_to_instrument(lockin, SR830_MAPPING)

    # keithley = instruments["keithley"] = Keithley_2400("keithley", "GPIB1::27::INSTR")
    # add_mapping_to_instrument(keithley, KEITHLEY_2400_MAPPING)

    return instruments


if __name__ == "__main__":
    parser = argparse.ArgumentParser("qtools")
    parser.add_argument(
        "-m",
        "--metadata",
        type=argparse.FileType("r"),
        help="YAML-file with metadata information.",
    )
    args = parser.parse_args()

    # Load metadata
    db.api_url = "http://134.61.7.48:9123"
    with args.metadata or open("metadata.yaml") as f:
        metadata = Metadata.from_yaml(f)
    metadata.save()

    # Create station with instruments
    station = Station()
    instruments = _initialize_instruments()
    for name, instrument in instruments.items():
        station.add_component(instrument)

    # Uncomment the following part, to generate a mapping stub file from an initialized instrument
    # from qtools.instrument.mapping.base import _generate_mapping_stub
    # _generate_mapping_stub(instruments["keithley"], "qtools/instrument/mapping/tektronix/Keithley_2400.json")
    # exit()

    # Load measuring script template
    script = InducingMeasurementScript()
    script.setup()

    # map gate functions to instruments
    map_gates_to_instruments(station.components, script.gate_parameters)

    # run script
    script.run()

    # Exit
    raise SystemExit(0)
