"""
Test modules for:

meticulous.__main__
"""
from __future__ import absolute_import, division, print_function

import pytest

from meticulous.__main__ import main


@pytest.mark.parametrize("args,", [("bogus",)])
def test_main(args):
    """
    GIVEN the .__main__ module entry point WHEN calling main THEN the call
    executes successfully with a result of `None`
    """
    # Setup
    from click.testing import CliRunner

    runner = CliRunner()
    # Exercise
    fullargs = list(args)
    result = runner.invoke(main, fullargs)
    # Verify
    assert "No such command" in result.output  # noqa: S101 # nosec
