"""
Module load handler for execution via:

python -m meticulous
"""
from __future__ import absolute_import, division, print_function

import click

from meticulous._github import is_archived
from meticulous._process import run_invocation

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

__version__ = "0.1"


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__)
@click.option("--target", nargs=1)
@click.pass_context
def main(ctxt, target):
    """
    Main click group handler
    """
    if ctxt.invoked_subcommand is None:
        run_invocation(target)


@main.command()
@click.option("--target", nargs=1)
def invoke(target):
    """
    Primary command handler
    """
    run_invocation(target)


@main.command()
def test():
    """
    Test command handler
    """
    print(is_archived("kennethreitz/clint"))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
