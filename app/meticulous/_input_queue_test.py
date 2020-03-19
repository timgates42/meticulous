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
    manager.add({"priority": 10, "name": "later"})
    manager.add({"priority": 1, "name": "now"})
    # Exercise
    task = manager.pop()
    # Verify
    assert task["name"] == "now"  # noqa=S101 # nosec


def test_save():
    """
    Ensure tasks are pulled off for suspension
    """
    # Setup
    manager = get_input_queue()
    manager.add({"priority": 10, "name": "later"})
    manager.add({"priority": 1, "name": "now"})
    # Exercise
    tasks = manager.save()
    # Verify
    assert tasks == [  # noqa=S101 # nosec
        {"priority": 1, "name": "now"},
        {"priority": 10, "name": "later"},
    ]
