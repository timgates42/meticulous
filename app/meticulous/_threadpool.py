"""
Multithread processing to maximize time value of user input
"""

import collections
import concurrent.futures
import logging
import threading

from meticulous._progress import add_progress, clear_progress

Context = collections.namedtuple("Context", ["taskjson", "controller"])


class PoolManager:
    """
    Used to add tasks that must be json serializable to pass to threads for
    execution or if requiring input saved to the user input priority heap.
    """

    def __init__(self, handlers, max_workers):
        self._handlers = handlers
        self._executor = None
        self._max_workers = max_workers
        self._draining = False
        self._saved = []
        self._futures = []

    def add(self, taskjson, controller):
        """
        add a task to the executor
        """
        if self._draining or self._executor is None:
            raise Exception("No new tasks when draining.")
        future = self._executor.submit(
            self.run_task, taskjson=taskjson, controller=controller
        )
        self._futures.append(future)

    def run_task(self, taskjson, controller):
        """
        Called by a thread in the pool to run the task
        """
        threading.local().worker = True
        try:
            if self._draining:
                self._saved.append(taskjson)
                return
            tid = threading.current_thread().ident
            key = ("worker", tid)
            try:
                msg = f"Starting job {taskjson!r}"
                add_progress(key, msg)
                handler = self.load_handler(taskjson, controller)
                handler()
            finally:
                clear_progress(key)
        except Exception:  # pylint: disable=broad-except
            logging.exception("Unhandled error")

    def load_handler(self, taskjson, controller):
        """
        Lookup the handlers to return a task
        """
        factory = self._handlers[taskjson["name"]]
        return factory(Context(taskjson=taskjson, controller=controller))

    def stop(self):
        """
        Wait for current tasks to complete
        """
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

    def __enter__(self):
        """
        Implement python with interface
        """
        # pylint: disable=consider-using-with
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers
        )
        return self

    def __exit__(self, type, value, traceback):  # pylint: disable=redefined-builtin
        """
        Implement python with interface
        """
        self.stop()

    def drain(self):
        """
        Signal to stop executing new tasks
        """
        self._draining = True

    def save(self):
        """
        Shutdown and collect and saved results
        """
        self.drain()
        self.stop()
        return self._saved

    def empty(self):
        """
        Check if threadpool executor has nothing to do
        """
        return all(future.done() for future in self._futures)


def get_pool(handlers, max_workers=5):
    """
    Obtain a threadpool
    """
    return PoolManager(handlers, max_workers)


def main(handlers):
    """
    Main entry point to run pool manager
    """
    with get_pool(handlers) as pool:
        return pool.save()
