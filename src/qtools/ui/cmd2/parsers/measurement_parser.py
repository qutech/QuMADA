import argparse

import json

from cmd2 import Cmd, Cmd2ArgumentParser, CommandSet, with_argparser

from qtools.instrument.mapping.base import map_gates_to_instruments


class MeasurementCommandSet(CommandSet):
    def choices_complete_measurement_scripts(self) -> list[str]:
        return list(self._cmd.measurement_scripts.keys())

    # Measurement parsers
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
    
    parser_measurement_setup.add_argument(
        "-p",
        "--parameters",
        type=argparse.FileType("r"),
        help="File path of the measurement parameters",
        completer=Cmd.path_complete,
    )

    # measurement run
    parser_measurement_run = measurement_subparsers.add_parser(
        "run", help="Run the measurement."
    )

    # measurement map_gates
    parser_measurement_map_gates = measurement_subparsers.add_parser(
        "map_gates", help="Map gates to instruments."
    )

    # functions
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
                self._cmd.script = self._cmd.measurement_scripts[args.name]()

        else:
            raise ValueError(
                "More than one location for the script specified. Use --pid, --name or --file exclusively."
            )

    def measurement_setup(self, args):
        parameters = json.load(args.parameters)
        self._cmd.script.setup(parameters=parameters, metadata=self._cmd.metadata)

    def measurement_run(self, args):
        self._cmd.script.run()

    def measurement_map_gates(self, args):
        map_gates_to_instruments(
            self._cmd.station.components, self._cmd.script.gate_parameters
        )

    def measurement_script_run(self, args):
        self.measurement_script_load(args)
        self.measurement_setup(args)
        self.measurement_map_gates(args)
        self.measurement_run(args)

    # function mapping
    parser_measurement_script_load.set_defaults(func=measurement_script_load)
    parser_measurement_script_run.set_defaults(func=measurement_script_run)
    parser_measurement_setup.set_defaults(func=measurement_setup)
    parser_measurement_run.set_defaults(func=measurement_run)
    parser_measurement_map_gates.set_defaults(func=measurement_map_gates)

    # general subcommand parser
    @with_argparser(measurement_parser)
    def do_measurement(self, args):
        """measurement command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self._cmd.do_help("measurement")
