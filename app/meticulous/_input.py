"""
Common user input utilities.
"""

from PyInquirer import prompt


class UserCancel(Exception):
    """
    Raised if a user cancels an input.
    """


def make_simple_choice(choices, message="What do you want to do?"):
    """
    Make a choice using a simple {key: key} list of choices
    """
    return make_choice({choice: choice for choice in choices}, message=message)


def make_choice(choices, message="What do you want to do?"):
    """
    Call PyInquirer/prompt-toolkit to make a choice
    """
    choicelist = sorted(list(choices.keys()))
    choicelist.append("- quit -")
    menu = [
        {"type": "list", "name": "option", "message": message, "choices": choicelist}
    ]
    answers = prompt(menu)
    option = answers.get("option", "- quit -")
    return check_cancel(choices.get(option))


def get_confirmation(message="Do you want to continue", defaultval=True):
    """
    Call PyInquirer/prompt-toolkit to make a confirmation
    """
    menu = [
        {"type": "confirm", "message": message, "name": "choice", "default": defaultval}
    ]
    answers = prompt(menu)
    return check_cancel(answers.get("choice"))


def check_cancel(result):
    """
    Raise an exception for cancellations.
    """
    if result is None:
        raise UserCancel()
    return result


def get_input(message, defaultval=""):
    """
    Call PyInquirer/prompt-toolkit to make a simple input
    """
    menu = [
        {"type": "input", "name": "option", "message": message, "default": defaultval}
    ]
    answers = prompt(menu)
    return check_cancel(answers.get("option"))


if __name__ == "__main__":
    print(repr(get_confirmation("Test?")))
    print(repr(make_simple_choice(["A", "B"])))
    print(repr(get_input("Test?")))
