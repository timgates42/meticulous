"""
Test modules for:

module_goes_here.__main__
"""

from module_goes_here.__main__ import main


def test_main():
    """
    GIVEN the .__main__ module entry point WHEN calling main THEN the call
    executes successfully with a result of `None`
    """
    # Setup
    # Exercise
    result = main()  # pylint: disable=assignment-from-no-return
    # Verify
    assert result is None  # nosec
