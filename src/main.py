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
# from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.tests.instrument_mocks import DummyInstrument, DummyInstrumentWithMeasurement
from qcodes.utils.metadata import Metadatable

from qtools.data.measurement import FunctionType as ft
from qtools.instrument.mapping.base import MappingError, filter_flatten_parameters, add_mapping_to_instrument
from qtools.measurement.measurement_for_immediate_use.inducing_measurement import InducingMeasurementScript
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
        MutableMapping[Any, EquipmentInstance]: Instruments, that can be loaded into qcodes Station.#
    """
    qc.Instrument.close_all() # Remove all previous initialized instruments
    
    # TODO: Maybe do this in UI
    instruments: dict[str, Instrument] = {}

    dac = instruments["dac"] = Decadac("dac",
                                        "ASRL6::INSTR",
                                        min_val=-10, max_val=10,
                                        terminator="\n")
    add_mapping_to_instrument(dac, "qtools/instrument/mapping/Decadac.json")
    
    # dac = instruments["dac"] = DummyInstrument("dac", ("voltage", "current"))
    # instruments["dmm"] = DummyInstrumentWithMeasurement("dmm", dac)

    lockin = instruments["lockin"] = SR830("lockin", "GPIB1::12::INSTR")
    add_mapping_to_instrument(lockin, "qtools/instrument/mapping/lockin.json")
    
    keithley = instruments["keithley"] = Keithley_2400("keithley", "GPIB1::27::INSTR")
    add_mapping_to_instrument(keithley, "qtools/instrument/mapping/tektronix/Keithley_2400.json")
    return instruments


def map_gates_to_instruments(components: Mapping[Any, Metadatable],
                             gate_parameters: Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]) -> None:
    """
    Maps the gates, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components (Mapping[Any, Metadatable]): Instruments/Components in QCoDeS
        gate_parameters (Mapping[Any, Union[Mapping[Any, Parameter], Parameter]]): Gates, as defined in the measurement script
    """
    for key, gate in gate_parameters.items():
        if isinstance(gate, Parameter):
            # map parameters
            pass
        else:
            # map gate to instrument
            print(f"Mapping gate {key} to one of the following instruments:")
            for idx, instrument_key in enumerate(components.keys()):
                print(f"{idx}: {instrument_key}")
            chosen = None
            while True:
                try:
                    chosen = int(input(f"Which instrument shall be mapped to gate \"{gate}\": "))
                    chosen_instrument = list(components.values())[int(chosen)]
                    try:
                        _map_gate_to_instrument(gate, chosen_instrument)
                    except MappingError:
                        # Could not map instrument, do it manually
                        # TODO: Map to multiple instruments
                        _map_gate_parameters_to_instrument_parameters(gate, chosen_instrument)
                    break
                except (IndexError, ValueError):
                    continue


def _map_gate_to_instrument(gate: Mapping[Any, Parameter],
                            instrument: Metadatable) -> None:
    """
    Maps the gate parameters of one specific gate to the parameters of one specific instrument.

    Args:
        gate (Mapping[Any, Parameter]): Gate parameters
        instrument (Metadatable): Instrument in QCoDeS
    """ 
    instrument_parameters: Dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")}
    for key, parameter in gate.items():
        # Map only parameters, that are not set already
        if parameter is None:
            candidates = [parameter for parameter in mapped_parameters.values() if parameter._mapping == key and parameter not in gate.values()]
            try:
                gate[key] = candidates.pop()
            except IndexError:
                raise MappingError(f"No mapping candidate for \"{key}\" in instrument \"{instrument.name}\"")


def _map_gate_parameters_to_instrument_parameters(gate_parameters: Mapping[Any, Parameter],
                                                  instrument: Metadatable,
                                                  append_unmapped_parameters=True) -> None:
    """
    Maps the gate parameters of one specific gate to the instrument parameters of one specific instrument.

    Args:
        gate_parameters (Mapping[Any, Parameter]): Gate parameters
        instrument (Metadatable): Instrument in QCoDeS
    """
    instrument_parameters: Dict[Any, Parameter] = filter_flatten_parameters(instrument)
    mapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")}
    unmapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if not hasattr(parameter, "_mapping")}

    # This is ugly
    for key, parameter in gate_parameters.items():
        if parameter is None:
            # Filter instrument parameters, if _mapping attribute is equal to key_gp
            # if there is no mapping provided, append those parameters to the list
            candidates = {k: p for k, p in mapped_parameters.items() if p._mapping == key}
            if append_unmapped_parameters:
                candidates = candidates | unmapped_parameters
            candidates_keys = list(candidates.keys())
            candidates_values = list(candidates.values())
            print("Possible instrument parameters:")
            for idx, candidate_key in enumerate(candidates_keys):
                print(f"{idx}: {candidate_key}")
            chosen = None
            while True:
                try:
                    chosen = int(input(f"Please choose an instrument parameter for gate parameter \"{key_gp}\": "))
                    gate_parameters[key] = candidates_values[int(chosen)]
                    break
                except (IndexError, ValueError):
                    continue


if __name__ == "__main__":
    # Create station with instruments
    station = Station()
    instruments = _initialize_instruments()
    for name, instrument in instruments.items():
        station.add_component(instrument)
        
    # from qtools.instrument.mapping.base import _generate_mapping_stub
    # _generate_mapping_stub(instruments["keithley"], "qtools/instrument/mapping/tektronix/Keithley_2400.json")

    # Load measuring script template
    script = InducingMeasurementScript()
    script.setup()

    # map gate functions to instruments
    map_gates_to_instruments(station.components, script.gate_parameters)

    # run script
    script.run()
