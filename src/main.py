#!/usr/bin/env python3

from typing import Dict, Iterable, Mapping, MutableMapping, Any, Set, Tuple
from xml.dom.minicompat import StringTypes
from numpy import isin

from qcodes.instrument import Parameter
from qcodes.instrument.base import Instrument, InstrumentBase
from qcodes.instrument.channel import ChannelList
# from qcodes.instrument_drivers.Harvard.Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
# from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement
from qcodes.utils.metadata import Metadatable

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


def _map_gates_to_instruments(components: Mapping[Any, Metadatable], gate_parameters: Mapping[Any, Parameter]) -> None:
    """
    Maps the gate parameters, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components ([type]): Instruments/Components in QCoDeS
        gate_parameters (Mapping[Any, Parameter]): gate parameters, as defined in the measurement script
    """
    instrument_parameters: Dict[Any, Parameter] = {}
    seen: Set[int] = set()

    def _filter_flatten_parameters(node) -> None:
        """
        Recursively filters objects of Parameter types from data structure, that consists of dicts, lists and Metadatable.

        Args:
            node (Union[Dict, List, Metadatable]): Current/starting node in the data structure
        """
        # TODO: Handle InstrumentChannel
        values = list(node.values()) if isinstance(node, dict) else list(node)

        for value in values:
            if isinstance(value, Parameter):
                instrument_parameters[value.full_name] = value
            else:
                if isinstance(value, Iterable) and not isinstance(value, StringTypes):
                    _filter_flatten_parameters(value)
                elif isinstance(value, Metadatable):
                    # Object of some Metadatable type, try to get __dict__ and _filter_flatten_parameters
                    try:
                        value_hash = hash(value)
                        if value_hash not in seen:
                            seen.add(value_hash)
                            _filter_flatten_parameters(vars(value))
                    except TypeError:
                        # End of tree
                        pass

    _filter_flatten_parameters(components)

    # This is ugly
    for key_gp, gate_parameter in gate_parameters.items():
        if gate_parameter is None:
            keys_ip = list(instrument_parameters.keys())
            values_ip = list(instrument_parameters.values())
            print("Possible instrument parameters:")
            for idx, key_ip in enumerate(keys_ip):
                print(f"{idx}: {key_ip}")
            chosen = None
            while True:
                try:
                    chosen = int(input(f"Please choose an instrument parameter for gate parameter \"{key_gp}\": "))
                    gate_parameters[key_gp] = values_ip[int(chosen)]
                    break
                except (IndexError, ValueError):
                    continue


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
    _map_gates_to_instruments(station.components, script.channels)

    # run script
    script.run()
