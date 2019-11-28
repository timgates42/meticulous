"""
Module load handler for execution via:

python -m meticulous
"""
from __future__ import absolute_import, division, print_function

import os
import sys
from pathlib import Path

import click

from meticulous._github import check_forked, fork, checkout
from meticulous._sources import obtain_sources

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

__version__ = "0.1"


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__)
@click.option('--target', nargs=1)
@click.pass_context
def main(ctxt, target):
    """
    Main click group handler
    """
    if ctxt.invoked_subcommand is None:
        run_invocation(target)


@main.command()
@click.option('--target', nargs=1)
def invoke(target):
    """
    Primary command handler
    """
    run_invocation(target)


def run_invocation(target):
    """
    Execute the invocation
    """
    if target is None:
        target = Path(os.environ["HOME"]) / "data"
    else:
        target = Path(target)
    if not target.is_dir():
        print(f"Target {target} is not a directory.", file=sys.stderr)
        sys.exit(1)
    for orgrepo in obtain_sources():
        _, repo = orgrepo.split("/", 1)
        print(f"Checking {orgrepo}")
        if not check_forked(repo):
            print(f"Have not forked {orgrepo}")
            print(f"Forking {orgrepo}")
            fork(orgrepo)
            print(f"Checkout {repo}")
            checkout(repo, target)
            sys.exit(0)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
