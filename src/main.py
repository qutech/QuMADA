#!/usr/bin/env python3

from typing import Mapping, MutableMapping, Any
from collections.abc import Iterable

from qcodes.instrument import Parameter
from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
# from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement

from qtools.data.measurement import FunctionType as ft, VirtualParameter
from qtools.measurement.measurement import FunctionMapping, VirtualGate
from qtools.measurement.measurement import QtoolsStation as Station

import qtools.instrument.sims as qtsims
import qcodes.instrument.sims as qcsims

# DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
# KEITHLEY_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
# SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')


def _initialize_instruments() -> MutableMapping[Any, VisaInstrument]:
    """
    Initializes the instruments as qcodes components.

    Returns:
        MutableMapping[Any, EquipmentInstance]: Instruments, that can be loaded into qcodes Station.
    """
    # TODO: Maybe do this in UI
    instruments: dict[str, VisaInstrument] = {}

    dac = instruments["dac"] = Decadac("dac",
                                       "ASRL6::INSTR",
                                       min_val=-10, max_val=10,
                                       terminator="\n")
    # dac.channels.switch_pos.set(1)
    dac.channels.update_period.set(50)
    dac.channels.ramp(0, 0.3)

    instruments["lockin"] = SR830("lockin", "GPIB1::12::INSTR")
    instruments["keithley"] = Keithley2450("keithley", "GPIB1::11::INSTR")
    return instruments


def _load_script_template():
    import qtools.measurement.example_template_script as script
    return script


def _map_gates_to_instruments(components, gates: Mapping):
    # instruments
    dac = components["dac"]
    keithley = components["keithley"]
    lockin = components["lockin"]

    mapping: list[FunctionMapping] = [
        FunctionMapping("voltage_source_ac", ft.VOLTAGE_SOURCE_AC,
                        gates["source_drain"],
                        {"amplitude": lockin.amplitude,
                         "frequency": lockin.frequency,
                         "output_enable": None}
                        ),
        FunctionMapping("current_sense_ac", ft.CURRENT_SENSE_AC,
                        gates["source_drain"],
                        {"current": lockin.R,
                         "time_constant": lockin.time_constant,
                         "sensitivity": lockin.sensitivity}
                        ),
        FunctionMapping("voltage_source", ft.VOLTAGE_SOURCE,
                        gates["topgate"],
                        {"voltage": keithley.source.voltage,
                         "current_limit": keithley.source.limit,
                         "output_enable": keithley.output_enabled}
                        ),
        FunctionMapping("current_sense", ft.CURRENT_SENSE,
                        gates["topgate"],
                        {"current": keithley.sense.current})
    ]

    for fm in mapping:
        temp = VirtualParameter()
        for name, parameter in fm.parameters.items():
            setattr(temp, name, parameter)
        setattr(fm.gate, fm.name, temp)


if __name__ == "__main__":
    # Create station with instruments
    station = Station()
    instruments = _initialize_instruments()
    for name, instrument in instruments.items():
        station.add_component(instrument)

    # Load measuring script template
    script = _load_script_template()

    # setup measurement
    gates = script.setup()

    # map gate functions to instruments
    _map_gates_to_instruments(station.components, gates)

    # run script
    script.run(**gates)
