import argparse
import pprint

from cmd2 import Cmd, Cmd2ArgumentParser, CommandSet, with_argparser
from qcodes.instrument import VisaInstrument

from qtools.instrument.instrument import is_instrument_class
from qtools.instrument.mapping.base import (
    _generate_mapping_stub,
    add_mapping_to_instrument,
)


class InstrumentCommandSet(CommandSet):
    def choices_complete_instrument_drivers(self) -> list[str]:
        return list(self._cmd.instrument_drivers.keys())

    def choices_complete_instrument_mappings(self) -> list[str]:
        return [path.name for path in self._cmd.mappings]

    # Instrument parser
    instrument_parser = Cmd2ArgumentParser()
    instrument_subparsers = instrument_parser.add_subparsers(title="subcommands", help="subcommand help")

    # instrument list
    parser_instrument_list = instrument_subparsers.add_parser("list", help="List all initialized instruments.")
    parser_instrument_list.add_argument("--depth", default=1, type=int, help="depth of the snapshot to print")

    # instrument add
    parser_instrument_add = instrument_subparsers.add_parser("add", help="add instrument to station.")
    instrument_add_subparsers = parser_instrument_add.add_subparsers()

    # instrument add visa
    parser_instrument_add_visa = instrument_add_subparsers.add_parser("visa", help="Add VISA instrument to station.")
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
    parser_instrument_add_visa.add_argument("address", metavar="ADDRESS", help="VISA-address to the instrument.")
    parser_instrument_add_visa.add_argument("--visalib", help="VISAlib to use.")
    parser_instrument_add_visa.add_argument("--terminator", help="VISA terminator to use.")
    parser_instrument_add_visa.add_argument(
        "--mapping",
        help="Mapping file for the instrument",
        choices_provider=choices_complete_instrument_mappings,
    )

    # instrument add dummy
    parser_instrument_add_dummy = instrument_add_subparsers.add_parser("dummy", help="Add Dummy instrument to station.")
    parser_instrument_add_dummy.add_argument(
        "name",
        metavar="NAME",
        help="name of the instrument",
    )

    # instrument delete
    parser_instrument_delete = instrument_subparsers.add_parser("delete", help="Remove instrument from station.")
    parser_instrument_delete.add_argument("name", metavar="NAME", help="Name of the instrument.")

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
    parser_instrument_save_station = instrument_subparsers.add_parser("save_station", help="Save a station to file.")
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
    parser_instrument_generate_mapping.add_argument("name", metavar="NAME", help="Name of the instrument.")
    parser_instrument_generate_mapping.add_argument(
        "file",
        metavar="FILE",
        type=argparse.FileType("w"),
        help="Output file for the generated mapping.",
        completer=Cmd.path_complete,
    )

    # functions
    def instrument_list(self, args):
        pprint.pp(self._cmd.station.snapshot()["instruments"], depth=args.depth)

    def instrument_add(self, args):
        try:
            instrument_class: type[VisaInstrument] = self._cmd.instrument_drivers[args.driver]
            kwargs = {}
            if args.terminator:
                kwargs["terminator"] = args.terminator
            if args.visalib:
                kwargs["visalib"] = args.visalib
            instrument = instrument_class(name=args.name, address=args.address, **kwargs)
            if args.mapping:
                # This does not yet work correctly, because the chosen instrument name has to fit the name in the mapping file.
                path = next(p for p in self._cmd.mappings if p.name == args.mapping)
                add_mapping_to_instrument(instrument, path)
            self._cmd.station.add_component(instrument)

        except ImportError as e:
            self.pexcept(f"Error while importing Instrument Driver {args.name}: {e}")

    def instrument_add_dummy(self, args):
        ...
        raise NotImplementedError()

    def instrument_delete(self, args):
        self._cmd.station.remove_component(args.name)

    def instrument_load_station(self, args):
        self._cmd.station.load_config(args.file)

    def instrument_save_station(self, args):
        raise NotImplementedError()
        # Does this produce a valid station config file?
        # yaml.dump(self.station.snapshot(), args.file)

    def instrument_generate_mapping(self, args):
        # generate a mapping stub from an initialized instrument
        instrument = self._cmd.station.components[args.instrument]
        assert is_instrument_class(instrument)
        _generate_mapping_stub(instrument, args.file)

    # function mapping
    parser_instrument_list.set_defaults(func=instrument_list)
    parser_instrument_add_visa.set_defaults(func=instrument_add)
    parser_instrument_add_dummy.set_defaults(func=instrument_add_dummy)
    parser_instrument_delete.set_defaults(func=instrument_delete)
    parser_instrument_load_station.set_defaults(func=instrument_load_station)
    parser_instrument_save_station.set_defaults(func=instrument_save_station)
    parser_instrument_generate_mapping.set_defaults(func=instrument_generate_mapping)

    # general subcommand parser
    @with_argparser(instrument_parser)
    def do_instrument(self, args):
        """instrument command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self._cmd.do_help("instrument")
