"""
Test cases to ensure tasks are picked up and executed concurrently whilst
serializing user input
"""

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
    # Exercise
    pool.add({"name": "run"})
    # Verify
    pool.stop()
    assert result[0]
