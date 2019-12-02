"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import os
import sys
from pathlib import Path

from plumbum import FG, local
from spelling.check import check  # noqa=I001

from meticulous._github import check_forked, checkout, fork, is_archived
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, prepare, set_json_value
from PyInquirer import (  # noqa=I001 # pylint: disable=wrong-import-order
    prompt,  # noqa=I001
)  # noqa=I001

MAIN_MENU = [
    {
        "type": "list",
        "name": "option",
        "message": "What do you want to do?",
        "choices": [
            "add a new repository",
            "manually add a new repository",
            "examine a repository",
            "remove a repository",
            "- quit -",
        ],
    }
]

SELECT_REPO = {"type": "list", "name": "option", "message": "Which Repository?"}


class NoRepoException(Exception):
    """
    Raised if no repositories are available/selected
    """


def run_invocation(target):
    """
    Execute the invocation
    """
    if target is None:
        target = Path(os.environ["HOME"]) / "data"
    else:
        target = Path(target)
    if not target.is_dir():
        print(f"Target {target} is not a directory.", file=sys.stderr)
        sys.exit(1)
    prepare()
    while True:
        answers = prompt(MAIN_MENU)
        option = answers.get("option", "- quit -")
        try:
            if option == "examine a repository":
                examine_repo_selection()
            elif option == "manually add a new repository":
                manually_add_new_repo(target)
            elif option == "remove a repository":
                remove_repo_selection()
            elif option == "add a new repository":
                add_new_repo(target)
            elif option == "- quit -":
                print("Goodbye.")
                return
            else:
                print(f"Unknown option {option}.", file=sys.stderr)
                sys.exit(1)
        except NoRepoException:
            continue


def remove_repo_selection():
    """
    Select an available repository to remove
    """
    repo, _ = pick_repo()
    repository_map = get_json_value("repository_map", {})
    del repository_map[repo]
    set_json_value("repository_map", repository_map)


def examine_repo_selection():
    """
    Select an available repository to examine
    """
    _, repodir = pick_repo()
    examine_repo(repodir)


def pick_repo():
    """
    Select an available repository
    """
    repository_map = get_json_value("repository_map", {})
    if not repository_map:
        print("No repositories available.", file=sys.stderr)
        raise NoRepoException()
    choice = dict(SELECT_REPO)
    choices = list(repository_map.keys())
    choices.append("- quit -")
    choice["choices"] = choices
    answers = prompt([choice])
    option = answers.get("option", "- quit -")
    if option == "- quit -":
        raise NoRepoException()
    repodir = repository_map[option]
    return option, repodir


def examine_repo(repodir):
    """
    Inspect an available repository
    """
    print("Opening editor")
    editor = local["/usr/bin/vim"]
    with local.cwd(repodir):
        _ = editor["spelling.txt"] & FG


def manually_add_new_repo(target):
    """
    Allow entry of a new repository manually
    """
    choice = dict(SELECT_REPO)
    choices = sorted(os.listdir(target))
    choices.append("- quit -")
    choice["choices"] = choices
    answers = prompt([choice])
    option = answers.get("option", "- quit -")
    if option == "- quit -":
        raise NoRepoException()
    repository_map = get_json_value("repository_map", {})
    repository_map[option] = os.path.join(target, option)
    set_json_value("repository_map", repository_map)


def add_new_repo(target):
    """
    Locate a new repository and add it to the available set.
    """
    for orgrepo in obtain_sources():
        _, repo = orgrepo.split("/", 1)
        print(f"Checking {orgrepo}")
        if not check_forked(repo):
            print(f"Have not forked {orgrepo}")
            print(f"Forking {orgrepo}")
            fork(orgrepo)
            if is_archived(orgrepo):
                print(f"Skipping archived repo {orgrepo}")
                continue
            print(f"Checkout {repo}")
            checkout(repo, target)
            repodir = target / repo
            print(f"Running spell check on {repodir}")
            spellpath = repodir / "spelling.txt"
            print(f"Spelling output {spellpath}")
            with io.open(spellpath, "w", encoding="utf-8") as fobj:
                os.chdir(repodir)
                check(True, True, None, fobj)
            repository_map = get_json_value("repository_map", {})
            repository_map[repo] = str(repodir)
            set_json_value("repository_map", repository_map)
            return repo
    return None
