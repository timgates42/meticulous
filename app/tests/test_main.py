"""
Test modules for:

meticulous.__main__
"""
from __future__ import absolute_import, division, print_function

from meticulous.__main__ import main

import pytest


@pytest.mark.parametrize("args,", [(), ("check",)])
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
    assert result.output == "X\n"  # noqa: S101 # nosec
