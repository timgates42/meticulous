"""
Alternative way of running meticulous via slack conversations
"""

import datetime
import uuid
from threading import Condition, Thread

from meticulous._multiworker import Interaction, multiworker_core
from meticulous._progress import get_progress

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
        self.thread = None

    def response(self):
        """
        Return the current input requirement to the end user
        """
        raise NotImplementedError()

    def start(self, target):
        """
        Begin processing
        """
        if self.thread is not None:
            self.stop()
        self.thread = Thread(target=self.run, args=(target,), name="webworker")
        self.thread.start()

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
        self.thread.join()
        self.thread = None
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
        Handle form submission
        """
        if request.form.get("uuid") != str(self.uuid):
            return None
        val = request.form.get("choose")
        if val not in ["Yes", "No"]:
            return None
        state.respond(val == "Yes")
        return self.reload()


class Input(Awaiter):
    """
    Text Input
    """

    def handle(self, state):
        """
        Handle form submission
        """
        if request.form.get("uuid") != str(self.uuid):
            return None
        val = request.form.get("textinput")
        if val is None:
            return None
        state.respond(val)
        return self.reload()


class Choice(Awaiter):
    """
    Selection from choices
    """

    def handle(self, state):
        """
        Handle form submission
        """
        if request.form.get("uuid") != str(self.uuid):
            return None
        val = request.form.get("selection")
        if val is None:
            return None
        state.respond(self.choices.get(int(val)))
        return self.reload()


STATE = SlackStateHandler()

def main(target, start):
    """
    Alternative way of running meticulous via slack conversations
    """
    run_app(target, host, port)


def run_app(target, host, port):
    """
    Alternative way of running meticulous in a browser
    """
    STATE.start(target)
    try:
        APP.run(host=host, port=port)
    finally:
        STATE.stop()
