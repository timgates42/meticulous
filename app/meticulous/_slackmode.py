"""
Alternative way of running meticulous via slack conversations
"""

import datetime
import os
from threading import Condition

import slack

from meticulous._multiworker import Interaction, multiworker_core

INPUT = 0
CONFIRMATION = 1


class SlackStateHandler(Interaction):
    """
    Records the state to await user responses
    """

    def __init__(self):
        self.alive = False
        self.started_at = datetime.datetime.min
        self.condition = Condition()
        self.messages = []
        self.await_key = None
        self.response_val = None

    def response(self):
        """
        Return the current input requirement to the end user
        """
        raise NotImplementedError()

    def run(self, target):
        """
        Perform processing
        """
        self.started_at = datetime.datetime.now()
        self.alive = True
        while self.alive:
            multiworker_core(self, target)

    def stop(self):
        """
        Gracefully stop processing
        """
        self.alive = False
        self.started_at = datetime.datetime.min

    def get_input(self, message):
        return self.get_await(Input(message))

    def make_choice(self, choices, message="Please make a selection."):
        return self.get_await(Choice(choices, message))

    def check_quit(self, controller):
        return controller.tasks_empty()

    def get_confirmation(self, message="Do you want to continue", defaultval=True):
        return self.get_await(Confirmation(message, defaultval))

    def get_await(self, key):
        """
        Work out the user response
        """
        with self.condition:
            self.response_val = None
            self.await_key = key
            while self.response_val is None:
                self.condition.wait(10)
        return self.response_val

    def send(self, message):
        self.messages.append(message)

    def respond(self, val):
        """
        A response is chosen
        """
        with self.condition:
            self.await_key = None
            del self.messages[:]
            self.response_val = val
            self.condition.notify()


class Awaiter:
    """
    Waiting on some user input
    """

    def __init__(self):
        pass

    def handle(self, state):
        """
        Handle slack reposnse
        """
        raise NotImplementedError()

    def get_response(self):
        """
        Obtain the slack text prompt to send to user
        """
        raise NotImplementedError()


class Confirmation(Awaiter):
    """
    Yes/No
    """

    def handle(self, state):
        """
        Handle slack submission
        """


class Input(Awaiter):
    """
    Text Input
    """

    def handle(self, state):
        """
        Handle slack submission
        """


class Choice(Awaiter):
    """
    Selection from choices
    """

    def handle(self, state):
        """
        Handle slack submission
        """


STATE = SlackStateHandler()


@slack.RTMClient.run_on(event="message")
def rtm_message(**payload):
    """
    Message hook
    """
    print("msg")


def main(target, start):
    """
    Alternative way of running meticulous via slack conversations
    """
    slack_token = os.environ["SLACK_FAMILY_TOKEN"]
    rtm_client = slack.RTMClient(token=slack_token)
    rtm_client.start()
    STATE.run(target)
