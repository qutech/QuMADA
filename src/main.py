#!/usr/bin/env python3

from typing import Dict, Mapping, MutableMapping, Any, Tuple
from numpy import isin

from qcodes.instrument import Parameter
from qcodes.instrument.base import Instrument
# from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
# from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement

from qtools.data.measurement import FunctionType as ft
from qtools.measurement.example_template_script import MeasurementScript
from qtools.measurement.measurement import FunctionMapping, VirtualGate
from qtools.measurement.measurement import QtoolsStation as Station

# import qtools.instrument.sims as qtsims
import qcodes.instrument.sims as qcsims

# DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
KEITHLEY_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
# SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')


def _initialize_instruments() -> MutableMapping[Any, Instrument]:
    """
    Initializes the instruments as qcodes components.

    Returns:
        MutableMapping[Any, EquipmentInstance]: Instruments, that can be loaded into qcodes Station.
    """
    # TODO: Maybe do this in UI
    instruments: dict[str, Instrument] = {}

    # dac = instruments["dac"] = Decadac("dac",
    #                                    "ASRL6::INSTR",
    #                                    min_val=-10, max_val=10,
    #                                    terminator="\n")
    # dac.channels.switch_pos.set(1)
    # dac.channels.update_period.set(50)
    # dac.channels.ramp(0, 0.3)
    dac = instruments["dac"] = DummyInstrument("dac", ("voltage", "current"))
    instruments["dmm"] = DummyInstrumentWithMeasurement("dmm", dac)

    # instruments["lockin"] = SR830("lockin", "GPIB1::12::INSTR")
    instruments["keithley"] = Keithley2450("keithley", "GPIB::2::INSTR", visalib=KEITHLEY_VISALIB)
    return instruments


def _map_gates_to_instruments(station: Station, components: Mapping[Any, Instrument], channels: Mapping[Any, Parameter]) -> None:
    """
    Maps the channels, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components ([type]): Instruments/Components in QCoDeS
        channels (Mapping[Any, Parameter]): Channels, as defined in the measurement script
    """
    def fltr(node, types: Tuple):
        if isinstance(node, dict):
            ret_val = {}
            for key, val in node.items():
                if isinstance(val, types):
                    ret_val[key] = node[key]
                elif isinstance(node[key], list) or isinstance(node[key], dict):
                    child = fltr(node[key], types)
                    if child:
                        ret_val[key] = child
            if ret_val:
                return ret_val
            else:
                return None
        elif isinstance(node, list):
            ret_val = []
            for entry in node:
                child = fltr(entry, types)
                if child:
                    ret_val.append(child)
            if ret_val:
                return ret_val
            else:
                return None


    # Get all instruments from station components
    instruments = {key: item.__dict__ for key, item in components.items() if isinstance(item, Instrument)}
    # TODO: Recursively get parameters from Channels
    parameters = fltr(instruments, Parameter)
    pass


if __name__ == "__main__":
    # Create station with instruments
    station = Station()
    instruments = _initialize_instruments()
    for name, instrument in instruments.items():
        station.add_component(instrument)

    # Load measuring script template
    script = MeasurementScript()
    script.setup()

    # map gate functions to instruments
    _map_gates_to_instruments(station, station.components, script.channels)

    # run script
    script.run()
