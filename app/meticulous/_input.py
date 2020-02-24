"""
Common user input utilities.
"""

from PyInquirer import prompt


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
    return choices.get(option)


def get_confirmation(message="Do you want to continue", defaultval=True):
    """
    Call PyInquirer/prompt-toolkit to make a confirmation
    """
    menu = [
        {"type": "confirm", "message": message, "name": "choice", "default": defaultval}
    ]
    answers = prompt(menu)
    return answers.get("choice")


def get_input(message):
    """
    Call PyInquirer/prompt-toolkit to make a simple input
    """
    menu = [{"type": "input", "name": "option", "message": message}]
    answers = prompt(menu)
    option = answers.get("option")
    return option
