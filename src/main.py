#!/usr/bin/env python3

from typing import Dict, Iterable, Mapping, MutableMapping, Any, Set, Tuple

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
from qtools.instrument.mapping.base import filter_flatten_parameters, add_mapping_to_instrument
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
    keithley = instruments["keithley"] = Keithley2450("keithley", "GPIB::2::INSTR", visalib=KEITHLEY_VISALIB)
    add_mapping_to_instrument(keithley, "src/qtools/instrument/mapping/tektronix/Keithley_2450.json")
    return instruments


def _map_gates_to_instruments(components: Mapping[Any, Metadatable], gate_parameters: Mapping[Any, Parameter]) -> None:
    """
    Maps the gate parameters, that were defined in the MeasurementScript to the instruments, that are initialized in QCoDeS.

    Args:
        components ([type]): Instruments/Components in QCoDeS
        gate_parameters (Mapping[Any, Parameter]): gate parameters, as defined in the measurement script
    """
    instrument_parameters = filter_flatten_parameters(components)
    mapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if hasattr(parameter, "_mapping")}
    unmapped_parameters = {key: parameter for key, parameter in instrument_parameters.items() if not hasattr(parameter, "_mapping")}

    # This is ugly
    for key_g, gate in gate_parameters.items():
        if gate is None:
            gate = {"": gate}
        for key_gp, gate_parameter in gate.items():
            if gate_parameter is None:
                # Filter instrument parameters, if _mapping attribute is equal to key_gp
                # if there is no mapping provided, append those parameters to the list
                filtered_parameters = {key: parameter for key, parameter in mapped_parameters.items() if parameter._mapping == key_gp} | unmapped_parameters
                keys_ip = list(filtered_parameters.keys())
                values_ip = list(filtered_parameters.values())
                print("Possible instrument parameters:")
                for idx, key_ip in enumerate(keys_ip):
                    print(f"{idx}: {key_ip}")
                chosen = None
                while True:
                    try:
                        chosen = int(input(f"Please choose an instrument parameter for gate parameter \"{key_g}_{key_gp}\": "))
                        try:
                            gate_parameters[key_g][key_gp] = values_ip[int(chosen)]
                        except:
                            gate_parameters[key_g] = values_ip[int(chosen)]
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
    script = InducingMeasurementScript()
    script.setup()

    # map gate functions to instruments
    _map_gates_to_instruments(station.components, script.gate_parameters)

    # run script
    script.run()
