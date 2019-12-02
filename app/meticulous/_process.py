"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import os
import sys
from pathlib import Path

from plumbum import FG, local
from PyInquirer import prompt

from meticulous._github import check_forked, checkout, fork, is_archived
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, prepare, set_json_value
from spelling.check import check

MAIN_MENU = [
    {
        "type": "list",
        "name": "option",
        "message": "What do you want to do?",
        "choices": ["add a new repository", "examine a repository"],
    }
]

SELECT_REPO = {
    "type": "list",
    "name": "option",
    "message": "Which Repository?",
}


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
    answers = prompt(MAIN_MENU)
    option = answers["option"]
    if option == "examine a repository":
        examine_repo_selection()
    elif option == "add a new repository":
        add_new_repo(target)
    else:
        print(f"Unknown option {option}.", file=sys.stderr)
        sys.exit(1)


def examine_repo_selection():
    """
    Select an available repository
    """
    repository_map = get_json_value("repository_map", {})
    choice = dict(SELECT_REPO)
    choice["choices"] = repository_map.keys()
    answers = prompt([choice])
    print(repr(answers))


def examine_repo(repodir):
    """
    Inspect an available repository
    """
    print("Opening editor")
    editor = local["/usr/bin/vim"]
    with local.cwd(repodir):
        _ = editor["spelling.txt"] & FG


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
