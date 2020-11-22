"""
Prioritize and suspend user input queue
"""

import heapq


class InputQueue:
    """
    Manage user input queue
    """

    def __init__(self):
        self.queue = []

    def add(self, taskjson):
        """
        Add a user input request
        """
        priority = taskjson["priority"]
        heapq.heappush(self.queue, (priority, tuple(taskjson.items())))

    def pop(self):
        """
        Pull most important task
        """
        _, taskitems = heapq.heappop(self.queue)
        return dict(taskitems)

    def save(self):
        """
        Get json serialization of queue
        """
        result = []
        while self.queue:
            _, taskitems = heapq.heappop(self.queue)
            result.append(dict(taskitems))
        return result

    def peek(self):
        """
        Get most important task without removal
        """
        _, taskitems = self.queue[0]
        return dict(taskitems)

    def __repr__(self):
        return f"InputQueue({self.queue!r})"


def get_input_queue():
    """
    Get the user input manager
    """
    return InputQueue()
