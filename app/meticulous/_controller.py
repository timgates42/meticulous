"""
Manager user input and background tasks
"""


class Controller:
    """
    Manager user input and background tasks
    """

    def __init__(self, input_queue, threadpool):
        self._input_queue = input_queue
        self._threadpool = threadpool

    def add(self, task):
        """
        Check if the task is interactive and add to appropriate queue
        """
        interactive = task["interactive"]
        if interactive:
            self._input_queue.add(task)
        else:
            self._threadpool.add(task)
