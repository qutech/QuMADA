#!/usr/bin/env python3
import argparse
import inspect
import pprint
from typing import Any, MutableMapping, Type

import qcodes as qc
import qcodes.instrument.sims as qcsims
import yaml
from cmd2 import Cmd, Cmd2ArgumentParser, with_argparser
from qcodes.instrument.base import Instrument
from qcodes.instrument.visa import VisaInstrument
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
from qtools.utils.import_submodules import import_submodules
from qtools.utils.resources import import_resources

DECADAC_VISALIB = qtsims.__file__.replace('__init__.py', 'FZJ_Decadac.yaml@sim')
KEITHLEY_2450_VISALIB = qcsims.__file__.replace('__init__.py', 'Keithley_2450.yaml@sim')
SR830_VISALIB = qcsims.__file__.replace('__init__.py', 'SR830.yaml@sim')

def is_instrument(o):
    return inspect.isclass(o) and issubclass(o, Instrument)

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

        # import instruments
        modules = import_submodules("qcodes.instrument_drivers")
        self.instrument_drivers = {}
        for name, module in modules.items():
            members = inspect.getmembers(module, is_instrument)
            self.instrument_drivers.update(members)

        # import mappings
        self.mappings = import_resources("qtools.instrument.mapping", "*.json")

        # Metadata
        db.api_url = "http://134.61.7.48:9123"
        self.metadata = Metadata()
        self.station = Station()

    # argparse choices
    def choices_complete_instrument_drivers(self) -> list[str]:
        return list(self.instrument_drivers.keys())

    def choices_complete_instrument_mappings(self) -> list[str]:
        return [path.name for path in self.mappings]

    # Cmd2 Parsers
    metadata_parser = Cmd2ArgumentParser()
    metadata_subparsers = metadata_parser.add_subparsers(
        title="subcommands", help="subcommand help"
    )

    # metadata load
    parser_metadata_load = metadata_subparsers.add_parser(
        "load", help="Load a metadata object from a YAML-file."
    )
    parser_metadata_load.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("r"),
        help="YAML-file with metadata information.",
    )

    # metadata new
    parser_metadata_new = metadata_subparsers.add_parser(
        "new", help="Create an empty metadata object."
    )

    # metadata print
    parser_metadata_print = metadata_subparsers.add_parser(
        "print", help="print the metadata."
    )
    parser_metadata_print.add_argument(
        "-f",
        "--format",
        choices=["base", "yaml"],
        default="base",
        help="Output format.",
    )
    parser_metadata_print.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default="-",
        help="Output file to write the metadata to.",
    )

    instrument_parser = Cmd2ArgumentParser()
    instrument_subparsers = instrument_parser.add_subparsers(
        title="subcommands", help="subcommand help"
    )

    # instrument list
    parser_instrument_list = instrument_subparsers.add_parser(
        "list", help="List all initialized instruments."
    )
    parser_instrument_list.add_argument(
        "--depth", default=1, type=int, help="depth of the snapshot to print"
    )

    # instrument add
    parser_instrument_add = instrument_subparsers.add_parser(
        "add", help="add instrument to station."
    )
    instrument_add_subparsers = parser_instrument_add.add_subparsers()

    # instrument add visa
    parser_instrument_add_visa = instrument_add_subparsers.add_parser(
        "visa", help="add VISA instrument."
    )
    parser_instrument_add_visa.add_argument(
        "name",
        metavar="NAME",
        help="name of the instrument",
    )
    parser_instrument_add_visa.add_argument(
        "driver",
        metavar="DRIVER",
        help="Instrument driver",
        choices_provider=choices_complete_instrument_drivers,
    )
    parser_instrument_add_visa.add_argument(
        "address", metavar="ADDRESS", help="VISA-address to the instrument."
    )
    parser_instrument_add_visa.add_argument("--visalib", help="VISAlib to use.")
    parser_instrument_add_visa.add_argument(
        "--terminator", help="VISA terminator to use."
    )
    parser_instrument_add_visa.add_argument(
        "--mapping",
        help="Mapping file for the instrument",
        choices_provider=choices_complete_instrument_mappings,
    )

    # instrument add dummy
    parser_instrument_add_dummy = instrument_add_subparsers.add_parser(
        "dummy", help="add Dummy instrument."
    )
    parser_instrument_add_dummy.add_argument(
        "name",
        metavar="NAME",
        help="name of the instrument",
    )

    # instrument delete
    parser_instrument_delete = instrument_subparsers.add_parser(
        "delete", help="remove instrument from station."
    )
    parser_instrument_delete.add_argument(
        "name", metavar="NAME", help="Name of the instrument."
    )

    # instrument load_station
    parser_instrument_load_station = instrument_subparsers.add_parser(
        "load_station",
        help="load a station file with previously initialized instruments.",
    )
    parser_instrument_load_station.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("r"),
        help="File with the station object.",
    )

    # instrument save_station
    parser_instrument_save_station = instrument_subparsers.add_parser(
        "save_station", help="save a station to file."
    )
    parser_instrument_save_station.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("w"),
        help="Output file for the station object.",
    )

    # parser functions
    def instrument_list(self, args):
        pprint.pp(self.station.snapshot()["instruments"], depth=args.depth)

    def instrument_add(self, args):
        try:
            instrument_class: type[VisaInstrument] = self.instrument_drivers[
                args.driver
            ]
            kwargs = {}
            if args.terminator:
                kwargs["terminator"] = args.terminator
            if args.visalib:
                kwargs["visalib"] = args.visalib
            instrument = instrument_class(
                name=args.name, address=args.address, **kwargs
            )
            if args.mapping:
                # This does not yet work correctly, because the chosen instrument name has to fit the name in the mapping file.
                path = next(p for p in self.mappings if p.name == args.mapping)
                add_mapping_to_instrument(instrument, path)
            self.station.add_component(instrument)

        except ImportError as e:
            self.pexcept(f"Error while importing Instrument Driver {args.name}: {e}")

    def instrument_add_dummy(self, args):
        raise NotImplementedError()

    def instrument_delete(self, args):
        self.station.remove_component(args.name)

    def instrument_load_station(self, args):
        self.station.load_config(args.file)

    def instrument_save_station(self, args):
        raise NotImplementedError()
        # Does this produce a valid station config file?
        # yaml.dump(self.station.snapshot(), args.file)

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

    parser_instrument_list.set_defaults(func=instrument_list)
    parser_instrument_add_visa.set_defaults(func=instrument_add)
    parser_instrument_add_dummy.set_defaults(func=instrument_add_dummy)
    parser_instrument_delete.set_defaults(func=instrument_delete)
    parser_instrument_load_station.set_defaults(func=instrument_load_station)
    parser_instrument_save_station.set_defaults(func=instrument_save_station)
    parser_metadata_load.set_defaults(func=metadata_load)
    parser_metadata_new.set_defaults(func=metadata_new)
    parser_metadata_print.set_defaults(func=metadata_print)

    # general subcommand parser
    @with_argparser(metadata_parser)
    def do_metadata(self, args):
        """metadata command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self.do_help("metadata")

    @with_argparser(instrument_parser)
    def do_instrument(self, args):
        """instrument command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self.do_help("instrument")


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
