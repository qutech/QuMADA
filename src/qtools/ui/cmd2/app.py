import argparse
import inspect
import pprint

import yaml
from cmd2 import Cmd, Cmd2ArgumentParser, with_argparser
from qcodes import Station
from qcodes.instrument.base import Instrument
from qcodes.instrument.visa import VisaInstrument

import qtools.data.db as db
from qtools.data.metadata import Metadata
from qtools.instrument.instrument import is_instrument
from qtools.instrument.mapping.base import (
    _generate_mapping_stub,
    add_mapping_to_instrument,
    map_gates_to_instruments,
)
from qtools.measurement.measurement import is_measurement_script
from qtools.utils.import_submodules import import_submodules
from qtools.utils.resources import import_resources


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
        for _, module in modules.items():
            members = inspect.getmembers(module, is_instrument)
            self.instrument_drivers.update(members)

        # import mappings
        self.mappings = import_resources("qtools.instrument.mapping", "*.json")

        # import scripts
        modules = import_submodules("qtools.measurement.scripts")
        self.measurement_scripts = {}
        for _, module in modules.items():
            members = inspect.getmembers(module, is_measurement_script)
            self.measurement_scripts.update(members)

        # Metadata
        db.api_url = "http://134.61.7.48:9123"
        self.metadata = Metadata()
        self.station = Station()

    # argparse choices
    def choices_complete_instrument_drivers(self) -> list[str]:
        return list(self.instrument_drivers.keys())

    def choices_complete_instrument_mappings(self) -> list[str]:
        return [path.name for path in self.mappings]

    def choices_complete_measurement_scripts(self) -> list[str]:
        return list(self.measurement_scripts.keys())

    # Cmd2 Parsers
    metadata_parser = Cmd2ArgumentParser()
    metadata_subparsers = metadata_parser.add_subparsers(
        title="subcommands", help="subcommand help"
    )

    # metadata load
    parser_metadata_load = metadata_subparsers.add_parser(
        "load", help="Loads a metadata object from a YAML-file."
    )
    parser_metadata_load.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("r"),
        help="YAML-file with metadata information.",
        completer=Cmd.path_complete,
    )

    # metadata new
    parser_metadata_new = metadata_subparsers.add_parser(
        "new", help="Create an empty metadata object."
    )

    # metadata print
    parser_metadata_print = metadata_subparsers.add_parser(
        "print", help="Print the metadata."
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

    # instrument parser
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
        "visa", help="Add VISA instrument to station."
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
        "dummy", help="Add Dummy instrument to station."
    )
    parser_instrument_add_dummy.add_argument(
        "name",
        metavar="NAME",
        help="name of the instrument",
    )

    # instrument delete
    parser_instrument_delete = instrument_subparsers.add_parser(
        "delete", help="Remove instrument from station."
    )
    parser_instrument_delete.add_argument(
        "name", metavar="NAME", help="Name of the instrument."
    )

    # instrument load_station
    parser_instrument_load_station = instrument_subparsers.add_parser(
        "load_station",
        help="Load a station file with previously initialized instruments.",
    )
    parser_instrument_load_station.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("r"),
        help="File with the station object.",
        completer=Cmd.path_complete,
    )

    # instrument save_station
    parser_instrument_save_station = instrument_subparsers.add_parser(
        "save_station", help="Save a station to file."
    )
    parser_instrument_save_station.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("w"),
        help="Output file for the station object.",
        completer=Cmd.path_complete,
    )

    # instrument generate_mapping
    parser_instrument_generate_mapping = instrument_subparsers.add_parser(
        "generate_mapping",
        help="Generate a mapping stub from an initialized instrument.",
    )
    parser_instrument_generate_mapping.add_argument(
        "name", metavar="NAME", help="Name of the instrument."
    )
    parser_instrument_generate_mapping.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("w"),
        help="Output file for the generated mapping.",
        completer=Cmd.path_complete,
    )

    # measurement parser
    measurement_parser = Cmd2ArgumentParser()
    measurement_subparsers = measurement_parser.add_subparsers(
        title="subcommands", help="subcommands help"
    )

    # measurement script
    parser_measurement_script = measurement_subparsers.add_parser(
        "script", help="measurement script commands"
    )
    measurement_script_subparsers = parser_measurement_script.add_subparsers()

    # measurement script load
    parser_measurement_script_load = measurement_script_subparsers.add_parser(
        "load", help="Loads a measurement script."
    )
    parser_measurement_script_load.add_argument(
        "-n",
        "--name",
        help="Load measurement script by name.",
        choices_provider=choices_complete_measurement_scripts,
    )
    parser_measurement_script_load.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        help="File path of the measurement script.",
        completer=Cmd.path_complete,
    )
    parser_measurement_script_load.add_argument(
        "-pid", "--pid", help="pid to load script from database."
    )

    # measurement script run
    parser_measurement_script_run = measurement_script_subparsers.add_parser(
        "run", help="Loads, setups and runs a measurement script."
    )
    parser_measurement_script_run.add_argument(
        "-n",
        "--name",
        help="Load measurement script by name.",
        choices_provider=choices_complete_measurement_scripts,
    )
    parser_measurement_script_run.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r"),
        help="File path of the measurement script.",
        completer=Cmd.path_complete,
    )
    parser_measurement_script_run.add_argument(
        "-pid", "--pid", help="pid to load script from database."
    )

    # measurement setup
    parser_measurement_setup = measurement_subparsers.add_parser(
        "setup", help="Setup the measurement."
    )

    # measurement run
    parser_measurement_run = measurement_subparsers.add_parser(
        "run", help="Run the measurement."
    )

    # measurement map_gates
    parser_measurement_map_gates = measurement_subparsers.add_parser(
        "map_gates", help="Map gates to instruments."
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
        ...
        raise NotImplementedError()

    def instrument_delete(self, args):
        self.station.remove_component(args.name)

    def instrument_load_station(self, args):
        self.station.load_config(args.file)

    def instrument_save_station(self, args):
        raise NotImplementedError()
        # Does this produce a valid station config file?
        # yaml.dump(self.station.snapshot(), args.file)

    def instrument_generate_mapping(self, args):
        # generate a mapping stub from an initialized instrument
        instrument = self.station.components[args.instrument]
        assert isinstance(instrument, Instrument)
        _generate_mapping_stub(instrument, args.file)

    def measurement_script_load(self, args):
        def single_true(iterable):
            # check if only one entry is true
            i = iter(iterable)
            return any(i) and not any(i)

        if single_true([args.pid, args.name, args.file]):
            if args.pid:
                raise NotImplementedError()
            elif args.file:
                raise NotImplementedError()
            elif args.name:
                # Create script object
                self.script = self.measurement_scripts[args.name]()

        else:
            raise ValueError(
                "More than one location for the script specified. Use --pid, --name or --file exclusively."
            )

    def measurement_setup(self, args):
        self.script.setup()

    def measurement_run(self, args):
        self.script.run()

    def measurement_map_gates(self, args):
        map_gates_to_instruments(self.station.components, self.script.gate_parameters)

    def measurement_script_run(self, args):
        self.measurement_script_load(args)
        self.measurement_setup(args)
        self.measurement_map_gates(args)
        self.measurement_run(args)

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
    parser_instrument_list.set_defaults(func=instrument_list)
    parser_instrument_add_visa.set_defaults(func=instrument_add)
    parser_instrument_add_dummy.set_defaults(func=instrument_add_dummy)
    parser_instrument_delete.set_defaults(func=instrument_delete)
    parser_instrument_load_station.set_defaults(func=instrument_load_station)
    parser_instrument_save_station.set_defaults(func=instrument_save_station)
    parser_instrument_generate_mapping.set_defaults(func=instrument_generate_mapping)
    parser_measurement_script_load.set_defaults(func=measurement_script_load)
    parser_measurement_script_run.set_defaults(func=measurement_script_run)
    parser_measurement_setup.set_defaults(func=measurement_setup)
    parser_measurement_run.set_defaults(func=measurement_run)
    parser_measurement_map_gates.set_defaults(func=measurement_map_gates)

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

    @with_argparser(measurement_parser)
    def do_measurement(self, args):
        """measurement command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self.do_help("measurement")
