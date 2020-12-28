"""
Stores the current input requirement for the web requests to await their arrival
"""

import datetime
import uuid
from threading import Condition, Thread

from ansi2html import Ansi2HTMLConverter
from flask import request

from meticulous._multiworker import Interaction, multiworker_core
from meticulous._progress import get_progress

INPUT = 0
CONFIRMATION = 1


class StateHandler(Interaction):
    """
    Records the state to await user requests
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
        content = None
        if self.await_key is not None:
            content = self.await_key.handle(self)
        if content is None:
            conv = Ansi2HTMLConverter()
            content = "".join(conv.convert(msg) for msg in self.messages)
            if self.await_key is not None:
                content += self.await_key.get_html()
            else:
                progress = "<br />".join(
                    conv.convert(msg) for msg in get_progress()
                )
                content += f"""
No interaction required yet, will reload.<br />
{progress}
<script>
setTimeout("location.reload()", 500);
</script>
"""
        return """
<html>
<body>
<style>
input[type=button], input[type=submit], input[type=reset] {
  background-color: #4CAF50;
  border: none;
  color: white;
  padding: 16px 32px;
  text-decoration: none;
  margin: 4px 2px;
  cursor: pointer;
  -webkit-appearance: none;
}


table {
  width: 100%%;
}
</style>
%s
</body>
</html>
""" % (
            content,
        )

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
        self.uuid = uuid.uuid4()

    def get_form(self, content):
        """
        Get form submission html
        """
        return f"""
<form method="POST">
<input type="hidden" name="uuid" value="{self.uuid}">
{content}
</form>
"""

    @staticmethod
    def reload():
        """
        Request reloading after a short duration of processing
        """
        return """
Submission recorded, page will reload.
<script>
setTimeout("location.reload()", 500);
</script>
"""

    def handle(self, state):
        """
        Handle form submission
        """
        raise NotImplementedError()

    def get_html(self):
        """
        Obtain the request HTML
        """
        raise NotImplementedError()


class Confirmation(Awaiter):
    """
    Yes/No
    """

    def __init__(self, message, defaultval):
        super().__init__()
        conv = Ansi2HTMLConverter()
        self.content = conv.convert(message)
        self.defaultval = defaultval

    def get_form_button(self, val):
        """
        Get a simple pick a value form
        """
        return self.get_form(
            f"""
<input type="hidden" name="choose" value="{val}" />
<input type="submit" value="{val}" />
"""
        )

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

    def get_html(self):
        """
        Obtain the request HTML
        """
        formyes = self.get_form_button("Yes")
        formno = self.get_form_button("No")
        buttons = f"""
{self.content}<br/>
<table><tr><td>
{formyes}
</td><td>
&nbsp;
&nbsp;
&nbsp;
&nbsp;
</td><td>
{formno}
</td></tr></table>
"""
        return buttons


class Input(Awaiter):
    """
    Text Input
    """

    def __init__(self, message):
        super().__init__()
        conv = Ansi2HTMLConverter()
        self.content = conv.convert(message)

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

    def get_html(self):
        """
        Obtain the request HTML
        """
        textinput = f"""
{self.content}<br/>
<table><tr><td>
<input type="text" name="textinput" value="" />
</td><td>
<input type="submit" value="Save" />
</td></tr></table>
"""
        return self.get_form(textinput)


class Choice(Awaiter):
    """
    Selection from choices
    """

    def __init__(self, choices, message):
        super().__init__()
        conv = Ansi2HTMLConverter()
        self.content = conv.convert(message)
        options = list(enumerate(sorted(choices.keys())))
        self.choices = {index: choices[txt] for index, txt in options}
        self.options = "\n".join(
            f'<option value="{index}">{txt}</option>'
            for index, txt in options
        )

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

    def get_html(self):
        """
        Obtain the request HTML
        """
        selectform = f"""
{self.content}<br/>
<table><tr><td>
<select name="selection">{self.options}</select>
</td><td>
<input type="submit" value="Save" />
</td></tr></table>
"""
        return self.get_form(selectform)


STATE = StateHandler()
