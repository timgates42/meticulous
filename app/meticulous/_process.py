"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import os
import re
import sys
from pathlib import Path

from plumbum import FG, local
from PyInquirer import prompt
from spelling.check import check  # noqa=I001

from meticulous._github import check_forked, checkout, fork, is_archived
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, prepare, set_json_value

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
            "prepare a change",
            "- quit -",
        ],
    }
]

SELECT_REPO = {"type": "list", "name": "option", "message": "Which Repository?"}


class ProcessingFailed(Exception):
    """
    Raised if processing needs to go back to the main menu
    """


class NoRepoException(ProcessingFailed):
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
            elif option == "prepare a change":
                prepare_a_change()
            elif option == "- quit -":
                print("Goodbye.")
                return
            else:
                print(f"Unknown option {option}.", file=sys.stderr)
                sys.exit(1)
        except ProcessingFailed:
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


def prepare_a_change():
    """
    Select an available repository to prepare a change
    """
    _, repodir = pick_repo()
    add_change_for_repo(repodir)


def add_change_for_repo(repodir):
    """
    Work out the staged commit and prepare an issue and pull request based on
    the change
    """
    del_word, add_word, file_paths = get_typo(repodir)
    print(f"Changing {del_word} to {add_word} in {', '.join(file_paths)}")


def get_typo(repodir):
    """
    Look in the staged commit for the typo.
    """
    git = local["/usr/bin/git"]
    del_lines = []
    add_lines = []
    file_paths = []
    with local.cwd(repodir):
        output = git("diff", "--staged")
        for line in output.splitlines():
            if line.startswith('--- a/'):
                file_path = line[len('--- a/'):]
                file_paths.append(file_path)
        for line in output.splitlines():
            if line.startswith("- "):
                del_lines.append(line[2:])
            elif line.startswith("+ "):
                add_lines.append(line[2:])
    if len(del_lines) != 1 or len(add_lines) != 1:
        print("Could not read diff", file=sys.stderr)
        raise ProcessingFailed()
    del_words = re.findall("\\S+", del_lines[0])
    add_words = re.findall("\\S+", add_lines[0])
    for del_word, add_word in zip(del_words, add_words):
        if del_word != add_word:
            return del_word, add_word, file_paths
    print("Could not locate typo", file=sys.stderr)
    raise ProcessingFailed()


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
