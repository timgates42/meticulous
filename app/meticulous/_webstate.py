"""
Stores the current input requirement for the web requests to await their arrival
"""

import datetime


class StateHandler:
    """
    Records the state to await user requests
    """

    def __init__(self):
        self.alive = False
        self.started_at = datetime.datetime.min

    def response(self):
        """
        Return the current input requirement to the end user
        """
        alive_delta = datetime.datetime.now() - self.started_at
        return f"<html><body>{alive_delta}</body></html>"

    def start(self):
        """
        Begin processing
        """
        self.started_at = datetime.datetime.now()
        self.alive = True

    def stop(self):
        """
        Gracefully stop processing
        """
        self.alive = False
        self.started_at = datetime.datetime.min


STATE = StateHandler()
