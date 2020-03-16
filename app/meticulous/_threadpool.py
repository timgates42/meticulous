"""
Multithread processing to maximize time value of user input
"""

import concurrent.futures

from meticulous._input import get_confirmation


class WorkerContext(object):  # pylint: disable=too-few-public-methods
    """
    Used to record multithread state
    """

    def __init__(self):
        self.stopped = False
        self.count = 0

    def stop(self):
        """
        Called to cancel execution and save remaining tasks
        """
        self.stopped = True


def main(start_tasks, workers=5):
    """
    Start multithread worker processing of tasks
    """
    context = WorkerContext()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_iter = start_tasks(executor, context)
        for future in concurrent.futures.as_completed(future_iter):
            ask_continue = future.get_result()
            if ask_continue and not get_confirmation("Continue?"):
                context.stop()
