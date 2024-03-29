"""
Test cases to ensure tasks are picked up and executed concurrently whilst
serializing user input
"""

import threading

from meticulous._threadpool import get_pool


def test_add_async():
    """
    Check adding async task correctly runs
    """
    # Setup
    result = []

    def run():
        result.append(True)
        return result

    def load_run(_):
        return run

    pool = get_pool({"run": load_run})
    with pool:
        # Exercise
        pool.add({"name": "run"}, None)
        # Verify
        pool.stop()
    assert result[0]  # noqa=S101 # nosec


def test_shutdown():
    """
    Check saving async task beyond number of works suspends correctly
    """
    # Setup
    cond = threading.Condition()
    running = [0]

    def run():
        with cond:
            running[0] += 1
            cond.wait(60)

    def load_run(_):
        return run

    pool = get_pool({"run": load_run}, max_workers=2)
    with pool:
        taskjson = {"name": "run"}
        for _ in range(10):
            pool.add(taskjson, None)
        with cond:
            while running[0] < 2:
                cond.wait()
        pool.drain()
        with cond:
            cond.notify()
            cond.notify()
        pool.stop()
        # Exercise
        result = pool.save()
    # Verify
    assert result == ([taskjson] * 8)  # noqa=S101 # nosec
