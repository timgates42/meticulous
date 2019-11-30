"""
Handlers for checking existing forks and creating new ones.
"""

import sys

import github
from plumbum import FG, local

from meticulous._secrets import load_api_key
from meticulous._storage import get_value, set_value


def get_api():
    """
    Load the API Token from the secrets and return the API object
    """
    return github.Github(load_api_key())


def check_forked(repository):
    """
    Check cache to check for an existing fork
    """
    key = f"forked|{repository}"
    value = get_value(key)
    if value is None:
        result = _check_forked(repository)
        value = "Y" if result else "N"
        set_value(key, value)
    return value == "Y"


def _check_forked(repository):
    """
    Use the API to check for an existing fork
    """
    api = get_api()
    user_org = api.get_user().login
    try:
        api.get_repo(f"{user_org}/{repository}")
        return True
    except github.GithubException:
        return False


def fork(orgrepo):
    """
    Use the API to fork a repository
    """
    api = get_api()
    repo = api.get_repo(orgrepo)
    repo.create_fork()
    repository = orgrepo.split("/", 1)[-1]
    key = f"forked|{repository}"
    set_value(key, "Y")


def checkout(repo, target):
    """
    Clone a repository to under the target path
    if it does not already exist.
    """
    api = get_api()
    user_org = api.get_user().login
    clone_target = target / repo
    if clone_target.exists():
        print(f"{clone_target} already exists, clone aborted.", file=sys.stderr)
        sys.exit(1)
    git = local["/usr/bin/git"]
    with local.cwd(str(target)):
        _ = (
            git["clone", f"ssh://git@github.com/{user_org}/{repo}", str(clone_target)]
            & FG
        )


if __name__ == "__main__":
    print(check_forked("pylint"))
