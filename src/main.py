#!/usr/bin/env python3
import argparse
import pprint
from typing import Any, MutableMapping

import qcodes as qc
import qcodes.instrument.sims as qcsims
import yaml
from cmd2 import Cmd, Cmd2ArgumentParser, with_argparser
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

# Cmd2 Parsers
metadata_parser = Cmd2ArgumentParser()
metadata_subparsers = metadata_parser.add_subparsers(
    title="subcommands", help="subcommand help"
)

parser_metadata_load = metadata_subparsers.add_parser(
    "load", help="Load a metadata object from a YAML-file."
)
parser_metadata_load.add_argument(
    "file",
    metavar="FILE",
    type=argparse.FileType("r"),
    help="YAML-file with metadata information.",
)

parser_metadata_new = metadata_subparsers.add_parser(
    "new", help="Create an empty metadata object."
)

parser_metadata_print = metadata_subparsers.add_parser(
    "print", help="print the metadata."
)
parser_metadata_print.add_argument(
    "-f", "--format", choices=["base", "yaml"], default="base", help="Output format."
)
parser_metadata_print.add_argument(
    "-o",
    "--output",
    type=argparse.FileType("w"),
    default="-",
    help="Output file to write the metadata to.",
)


class QToolsApp(Cmd):
    def __init__(self):
        super().__init__()

        # remove cmd2 builtin commands
        del Cmd.do_edit
        del Cmd.do_shell
        # hide cmd2 builtin commands
        self.hidden_commands.append("alias")
        self.hidden_commands.append("macro")
        self.hidden_commands.append("run_pyscript")
        self.hidden_commands.append("run_script")
        self.hidden_commands.append("shortcuts")

        # Metadata
        db.api_url = "http://134.61.7.48:9123"
        self.metadata = Metadata()
        self.station = Station()

    def metadata_load(self, args):
        try:
            self.metadata = Metadata.from_yaml(args.file)
        except ValueError as e:
            self.pexcept(e)

    def metadata_new(self, args):
        self.metadata = Metadata()

    def metadata_print(self, args):
        if args.format == "base":
            # This output gets better with Python 3.10 (pprint support for dataclass)
            pprint.pp(self.metadata, stream=args.output)
        elif args.format == "yaml":
            yaml.dump(self.metadata, stream=args.output)

    parser_metadata_load.set_defaults(func=metadata_load)
    parser_metadata_new.set_defaults(func=metadata_new)
    parser_metadata_print.set_defaults(func=metadata_print)

    @with_argparser(metadata_parser)
    def do_metadata(self, args):
        """metadata command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self.do_help("metadata")


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
    app = QToolsApp()
    ret_code = app.cmdloop()
    raise SystemExit(ret_code)

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
