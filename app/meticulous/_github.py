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


def is_archived(orgrepo):
    """
    Check if a repository is archived
    """
    api = get_api()
    repo = api.get_repo(orgrepo)
    return repo.archived


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


def issues_allowed(reponame):
    """
    Check if issues disabled on the parent repository
    """
    repo = get_parent_repo(reponame)
    return repo.has_issues


def get_parent_repo(reponame):
    """
    Get the furthest ancestor repository that is not
    archived.
    """
    api = get_api()
    user_org = api.get_user().login
    repo = api.get_repo(f"{user_org}/{reponame}")
    while repo.parent and not repo.parent.archived:
        repo = repo.parent
    return repo


def get_true_orgrepo(orgrepo):
    """
    Check if an organization repository has been moved
    """
    api = get_api()
    repo = api.get_repo(orgrepo)
    return repo.full_name


if __name__ == "__main__":
    print(check_forked("pylint"))
