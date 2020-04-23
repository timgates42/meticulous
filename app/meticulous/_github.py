"""
Handlers for checking existing forks and creating new ones.
"""

import logging

import github
from plumbum import local

from meticulous._secrets import load_api_key
from meticulous._storage import get_value, set_value


def get_api():
    """
    Load the API Token from the secrets and return the API object
    """
    return github.Github(load_api_key())


def check_forked(orgrepo):
    """
    Check cache to check for an existing fork
    """
    repository = orgrepo.split("/", 1)[-1]
    key = f"forked|{repository}"
    value = get_value(key)
    if value == "Y":
        return True
    result = _check_forked(orgrepo)
    value = "Y" if result else "N"
    set_value(key, value)
    return value == "Y"


def _check_forked(orgrepo):
    """
    Use the API to check for an existing fork
    """
    repository = orgrepo.split("/", 1)[-1]
    if _check_forked_direct(repository):
        return True
    api = get_api()
    repo = api.get_repo(orgrepo)
    while repo.parent and not repo.parent.archived:
        repo = repo.parent
        orgrepo = repo.full_name
        repository = orgrepo.split("/", 1)[-1]
        if _check_forked_direct(repository):
            return True
    return False


def _check_forked_direct(repository):
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
        return
    git = local["/usr/bin/git"]
    with local.cwd(str(target)):
        git(
            "clone",
            "--depth=3",
            f"ssh://git@github.com/{user_org}/{repo}",
            str(clone_target),
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
    orgrepo = f"{user_org}/{reponame}"
    try:
        repo = api.get_repo(orgrepo)
    except github.GithubException:
        logging.exception("Failed to lookup %s", orgrepo)
        raise
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


def create_pr(reponame, title, body, from_branch, to_branch):
    """
    Use API to create a pull request
    """
    api = get_api()
    repo = get_parent_repo(reponame)
    user_org = api.get_user().login
    repo = get_parent_repo(reponame)
    pullreq = repo.create_pull(
        title=title, body=body, base=to_branch, head=f"{user_org}:{from_branch}"
    )
    return pullreq


if __name__ == "__main__":
    print(check_forked("pylint"))
