"""
Handlers for checking existing forks and creating new ones.
"""

import github

from meticulous._secrets import load_api_key


def get_api():
    """
    Load the API Token from the secrets and return the API object
    """
    return github.Github(load_api_key())


def check_forked(repository):
    """
    Use the API to check for an existing fork
    """
    api = get_api()
    return dir(api), repository


if __name__ == "__main__":
    print(check_forked("pylint"))
