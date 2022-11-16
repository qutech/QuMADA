import argparse
import pprint

import yaml
from cmd2 import Cmd, Cmd2ArgumentParser, CommandSet, with_argparser

from qtools_metadata.metadata import Metadata


class MetadataCommandSet(CommandSet):
    # Metadata parsers
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

    # functions
    def metadata_load(self, args):
        try:
            self._cmd.metadata = Metadata.from_yaml(args.file)
        except ValueError as e:
            self.pexcept(e)

    def metadata_new(self, args):
        self._cmd.metadata = Metadata()

    def metadata_print(self, args):
        if args.format == "base":
            # This output gets better with Python 3.10 (pprint support for dataclass)
            pprint.pp(self._cmd.metadata, stream=args.output)
        elif args.format == "yaml":
            yaml.dump(self._cmd.metadata, stream=args.output)

    # function mapping
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
            self._cmd.do_help("metadata")
