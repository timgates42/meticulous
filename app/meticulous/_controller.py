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

    def __enter__(self):
        """
        Implement python with interface
        """
        self._threadpool.__enter__()
        return self

    def __exit__(self, type, value, traceback):  # pylint: disable=redefined-builtin
        """
        Implement python with interface
        """
        self._threadpool.__exit__(type, value, traceback)
