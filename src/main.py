#!/usr/bin/env python3

from typing import Dict, Iterable, Mapping, MutableMapping, Any, Set, Tuple, Union
from numpy import isin

import qcodes as qc
from qcodes.instrument import Parameter
from qcodes.instrument.base import Instrument, InstrumentBase
from qcodes.instrument.channel import ChannelList
from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement
from qcodes.utils.metadata import Metadatable

from qtools.data.measurement import FunctionType as ft
from qtools.data.base import create_metadata_device
import qtools.data.db as db
from qtools.instrument.mapping.base import MappingError, add_mapping_to_instrument, map_gates_to_instruments
from qtools.measurement.measurement_for_immediate_use.inducing_measurement import InducingMeasurementScript
from qtools.measurement.measurement import FunctionMapping, VirtualGate
from qtools.measurement.measurement import QtoolsStation as Station


# Filenames for simulation files
import qtools.instrument.sims as qtsims
import qcodes.instrument.sims as qcsims
DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
KEITHLEY_2450_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')

# Filenames for mapping files
from qtools.instrument.mapping import DECADAC_MAPPING, SR830_MAPPING, KEITHLEY_2400_MAPPING, KEITHLEY_2450_MAPPING


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

    # Create Metadata structure
    db.api_url = "http://134.61.7.48:9123"
    device = create_metadata_device()
    device.save_to_db()

    # map gate functions to instruments
    map_gates_to_instruments(station.components, script.gate_parameters)

    # run script
    script.run()
