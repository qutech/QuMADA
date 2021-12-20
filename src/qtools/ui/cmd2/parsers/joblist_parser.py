import argparse
import pprint

from cmd2 import Cmd2ArgumentParser, CommandSet, with_argparser

from qtools.measurement.jobs import Job, Joblist


class JoblistCommandSet(CommandSet):
    def choices_joblist_jobs(self) -> list[str]:
        return [str(job) for job in self._cmd.joblist]

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
    parser_joblist_add.add_argument(
        "-c",
        "--clear",
        action="store_true",
        help="Clear the current job after adding it to the joblist.",
    )

    # joblist delete
    parser_joblist_delete = joblist_subparsers.add_parser(
        "delete", help="Removes a job from the joblist."
    )
    parser_joblist_delete.add_argument(
        "job",
        metavar="JOB",
        help="Job to delete.",
        choices_provider=choices_joblist_jobs,
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
        job: Job = self._cmd.current_job
        joblist: Joblist = self._cmd.joblist
        joblist.append(job)
        if args.clear:
            self._cmd.current_job = Job()

    def joblist_delete(self, args):
        raise NotImplementedError()

    def joblist_clear(self, args):
        self._cmd.joblist.clear()

    def joblist_run(self, args):
        joblist: Joblist = self._cmd.joblist
        for job in joblist:
            assert isinstance(job, Job)
            job._script.run()
        joblist.clear()

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
