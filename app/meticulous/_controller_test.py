"""
Test cases to check the controller
"""

from meticulous._controller import Controller
from meticulous._input_queue import get_input_queue
from meticulous._threadpool import get_pool


def test_add():
    """
    Ensure interactive tasks are added to the appropriate handler
    """
    # Setup
    input_queue = get_input_queue()
    threadpool = get_pool({})
    controller = Controller(input_queue=input_queue, threadpool=threadpool)
    task = {"interactive": True, "priority": 1}
    # Exercise
    controller.add(task)
    # Verify
    assert input_queue.pop() == task  # noqa=S101 # nosec
