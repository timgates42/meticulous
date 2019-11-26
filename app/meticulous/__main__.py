"""
Module load handler for execution via:

python -m meticulous
"""
from __future__ import absolute_import, division, print_function

import sys

import click

from meticulous._github import check_forked, fork
from meticulous._sources import obtain_sources

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

__version__ = "0.1"


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctxt):
    """
    Main click group handler
    """
    if ctxt.invoked_subcommand is None:
        run_invocation()


@main.command()
def invoke():
    """
    Primary command handler
    """
    run_invocation()


def run_invocation():
    """
    Execute the invocation
    """
    for orgrepo in obtain_sources():
        _, repo = orgrepo.split("/", 1)
        print(f"Checking {orgrepo}")
        if not check_forked(repo):
            print(f"Have not forked {orgrepo}")
            print(f"Forking {orgrepo}")
            fork(orgrepo)
            sys.exit(0)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
