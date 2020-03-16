"""
Multithread processing to maximize time value of user input
"""

import concurrent.futures


class PoolManager:
    """
    Used to add tasks that must be json serializable to pass to threads for
    execution or if requiring input saved to the user input priority heap.
    """
    def __init__(self, handlers, max_workers):
        self.handlers = handlers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def add(self, taskjson):
        """
        add a task to the executor
        """
        self.executor.submit(self.run_task, taskjson=taskjson)

    def run_task(self, taskjson):
        """
        Called by a thread in the pool to run the task
        """
        handler = self.load_handler(taskjson)
        handler()

    def load_handler(self, taskjson):
        """
        Lookup the handlers to return a task
        """
        factory = self.handlers[taskjson['name']]
        return factory(taskjson)

    def stop(self):
        """
        Wait for current tasks to complete
        """
        self.executor.shutdown()

    def __enter__(self):
        """
        Implement python with interface
        """
        return self

    def __exit__(self, type, value, traceback):  # pylint: disable=redefined-builtin
        """
        Implement python with interface
        """
        self.stop()


def get_pool(handlers, max_workers=5):
    """
    Obtain a threadpool
    """
    return PoolManager(handlers, max_workers)
