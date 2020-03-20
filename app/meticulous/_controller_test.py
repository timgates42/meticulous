"""
Test cases to check the controller
"""

import threading

from meticulous._controller import Controller
from meticulous._input_queue import get_input_queue
from meticulous._threadpool import get_pool


def test_add():
    """
    Ensure interactive tasks are added to the appropriate handler
    """
    # Setup
    input_queue = get_input_queue()
    handlers = {}
    threadpool = get_pool(handlers)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool
    )
    task = {"interactive": True, "priority": 1}
    # Exercise
    controller.add(task)
    # Verify
    assert input_queue.pop() == task  # noqa=S101 # nosec


def test_save():
    """
    Ensure tasks added get saved
    """
    # Setup
    cond = threading.Condition()

    def handle():
        with cond:
            cond.wait(10)

    def gen_handle(_):
        return handle

    input_queue = get_input_queue()
    handlers = {"1": gen_handle}
    threadpool = get_pool(handlers, max_workers=1)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool
    )
    task = {"interactive": True, "priority": 1}
    runtask = {"interactive": False, "name": "1"}
    pendingtask = {"interactive": False, "name": "1"}
    controller.add(task)
    controller.add(runtask)
    controller.add(pendingtask)
    threadpool.drain()
    with cond:
        cond.notify()
    # Exercise
    result = controller.save()
    # Verify
    assert result == [task, pendingtask]  # noqa=S101 # nosec


def test_user_shutdown():
    """
    Given an interactive task that requests shutdown confirm controller
    terminates
    """
    # Setup
    def gen_handle(context):
        def handle():
            context.controller.quit()

        return handle

    input_queue = get_input_queue()
    handlers = {"1": gen_handle}
    threadpool = get_pool(handlers)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool
    )
    task = {"interactive": True, "priority": 1, "name": "1"}
    nexttask = {"interactive": True, "priority": 2, "name": "1"}
    controller.add(task)
    controller.add(nexttask)
    # Exercise
    result = controller.run()
    # Verify
    assert result == [nexttask]  # noqa=S101 # nosec
