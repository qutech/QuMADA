import argparse
import pprint

from cmd2 import Cmd2ArgumentParser, CommandSet, with_argparser


class JoblistCommandSet(CommandSet):
    # Joblist parsers
    joblist_parser = Cmd2ArgumentParser()
    joblist_subparsers = joblist_parser.add_subparsers(
        title="subcommands", help="subcommand help"
    )

    # joblist print
    parser_joblist_print = joblist_subparsers.add_parser(
        "print", help="Print the joblist."
    )
    parser_joblist_print.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        default="-",
        help="Output file to write the metadata to.",
    )

    # joblist add
    parser_joblist_add = joblist_subparsers.add_parser(
        "add", help="Adds the current job to the joblist."
    )

    # joblist delete
    parser_joblist_delete = joblist_subparsers.add_parser(
        "delete", help="Removes a job from the joblist."
    )

    # joblist clear
    parser_joblist_clear = joblist_subparsers.add_parser(
        "clear", help="Clears the joblist."
    )

    # joblist run
    parser_joblist_run = joblist_subparsers.add_parser(
        "run", help="Run all jobs in the joblist."
    )

    # functions
    def joblist_print(self, args):
        pprint.pp(self._cmd.joblist, stream=args.output)

    def joblist_add(self, args):
        ...

    def joblist_delete(self, args):
        ...

    def joblist_clear(self, args):
        self._cmd.joblist.clear()

    def joblist_run(self, args):
        ...

    # function mapping
    parser_joblist_print.set_defaults(func=joblist_print)
    parser_joblist_add.set_defaults(func=joblist_add)
    parser_joblist_delete.set_defaults(func=joblist_delete)
    parser_joblist_clear.set_defaults(func=joblist_clear)
    parser_joblist_run.set_defaults(func=joblist_run)

    # general subcommand parser
    @with_argparser(joblist_parser)
    def do_joblist(self, args):
        """joblist command branching"""
        func = getattr(args, "func", None)
        if func:
            func(self, args)
        else:
            self._cmd.do_help("joblist")
