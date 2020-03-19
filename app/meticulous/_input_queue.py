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
        heapq.heappush(self.queue, (priority, taskjson))

    def pop(self):
        """
        Pull most important task
        """
        _, taskjson = heapq.heappop(self.queue)
        return taskjson

    def save(self):
        """
        Get json serialization of queue
        """
        result = []
        while self.queue:
            _, taskjson = heapq.heappop(self.queue)
            result.append(taskjson)
        return result


def get_input_queue():
    """
    Get the user input manager
    """
    return InputQueue()
