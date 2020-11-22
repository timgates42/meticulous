"""
In memory progress messages
"""


PROGRESS = {}


def add_progress(key, txt):
    """
    Record progress
    """
    PROGRESS[key] = txt


def clear_progress(key):
    """
    Remove progress
    """
    del PROGRESS[key]


def get_progress():
    """
    Obtain progress
    """
    return list(sorted(PROGRESS.values()))
