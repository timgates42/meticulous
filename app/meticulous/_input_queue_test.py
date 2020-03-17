"""
Testing input queue
"""

from meticulous._input_queue import get_input_queue


def test_priority():
    """
    Ensure a priority item is pulled first
    """
    # Setup
    manager = get_input_queue()
    manager.add(10, {"name": "later"})
    manager.add(1, {"name": "now"})
    # Exercise
    task = manager.pop()
    # Verify
    assert task["name"] == "now"  # noqa=S101 # nosec
