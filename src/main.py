#!/usr/bin/env python3

from typing import Mapping, MutableMapping, Any
from collections.abc import Iterable

from qcodes.instrument.visa import VisaInstrument
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450

from qtools.data.measurement import FunctionType as ft
from qtools.measurement.measurement import QtoolsStation as Station
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement

from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450

import qtools.instrument.sims as qtsims
import qcodes.instrument.sims as qcsims

DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
KEITHLEY_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')


def _initialize_instruments() -> MutableMapping[Any, VisaInstrument]:
    """
    Initializes the instruments as qcodes components.

    Returns:
        MutableMapping[Any, EquipmentInstance]: Instruments, that can be loaded into qcodes Station.
    """
    # TODO: Maybe do this in UI
    instruments: dict[str, VisaInstrument] = {}

    dac = instruments["dac"] = Decadac("dac",
                                       "GPIB::1::INSTR",
                                       visalib=DECADAC_VISALIB)
    dac.channels.switch_pos.set(1)
    dac.channels.update_period.set(50)
    dac.channels.ramp(0, 0.3)

    instruments["lockin"] = SR830("lockin", "GPIB::8::INSTR", terminator="\n", visalib=SR830_VISALIB)
    instruments["keithley"] = Keithley2450("keithley", "GPIB::2::INSTR", visalib=KEITHLEY_VISALIB)
    return instruments


def _load_script_template():
    import qtools.measurement.example_template_script as script
    return script


def _map_gates_to_instruments(components, gates: Mapping):

    def flatten(iterable):
        for elem in iterable:
            if isinstance(elem, Iterable) and not isinstance(elem, (str, bytes)):
                yield from flatten(elem)
            else:
                yield elem

    # flatten gate list
    gate_list = list(flatten(gates.values()))

    # instruments
    dac = components["dac"]

    # VOLTAGE_SOURCE
    gates_voltage_source = [gate for gate in gate_list if ft.VOLTAGE_SOURCE in gate.functions]
    for idx, gate in enumerate(gates_voltage_source):
        try:
            gate.volt = dac.channels[idx].volt

        except Exception:
            # Not enough channels
            raise

    # VOLTAGE_SENSE
    gates_voltage_sense = [gate for gate in gate_list if ft.VOLTAGE_SENSE in gate.functions]
    for gate in gates_voltage_sense:
        # TODO
        gate.volt = property()

    # CURRENT_SOURCE
    gates_current_source = [gate for gate in gate_list if ft.CURRENT_SOURCE in gate.functions]
    for gate in gates_current_source:
        # TODO
        gate.current = property()

    # CURRENT_SENSE
    gates_current_sense = [gate for gate in gate_list if ft.CURRENT_SENSE in gate.functions]
    for gate in gates_current_sense:
        # TODO
        gate.current = property()


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
