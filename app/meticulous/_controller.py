"""
Manager user input and background tasks
"""

import collections
import threading

Context = collections.namedtuple("Context", ["controller", "taskjson"])


class Controller:
    """
    Manager user input and background tasks
    """

    def __init__(self, handlers, input_queue, threadpool):
        self._handlers = handlers
        self._input_queue = input_queue
        self._threadpool = threadpool
        self._running = True
        self.condition = threading.Condition()

    def add(self, task):
        """
        Check if the task is interactive and add to appropriate queue
        """
        interactive = task["interactive"]
        if interactive:
            self._input_queue.add(task)
        else:
            self._threadpool.add(task)
        with self.condition:
            self.condition.notify()

    def peek_input(self):
        """
        Examine top input item without removal
        """
        return self._input_queue.peek()

    def tasks_empty(self):
        """
        Check if the threadpool is done
        """
        return self._threadpool.empty()

    def save(self):
        """
        Ensure processing is over and serialize tasks
        """
        self._threadpool.stop()
        result = []
        result.extend(self._input_queue.save())
        result.extend(self._threadpool.save())
        return result

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

    def run(self):
        """
        Pull off interactive tasks one at a time until the user quits and then
        save the state.
        """
        with self:
            while self._running:
                self.handle_input()
        return self.save()

    def handle_input(self):
        """
        Process one input task
        """
        task = self._input_queue.pop()
        factory = self._handlers[task["name"]]
        context = Context(controller=self, taskjson=task)
        handler = factory(context)
        return handler()

    def quit(self):
        """
        prevent further processing
        """
        self._running = False
