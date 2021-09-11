"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import os
import pathlib
import sys
from pathlib import Path

import spelling.version
import unanimous.util
import unanimous.version
from colorama import Fore, Style, init
from plumbum import FG, local
from workflow.engine import GenericWorkflowEngine

from meticulous._addrepo import interactive_add_one_new_repo, spelling_check
from meticulous._cleanup import remove_repo_for
from meticulous._constants import ALWAYS_BATCH_MODE
from meticulous._exceptions import NoRepoException, ProcessingFailed
from meticulous._input import (
    UserCancel,
    get_confirmation,
    make_choice,
    make_simple_choice,
)
from meticulous._multiworker import KeyboardInteraction, clear_work_queue
from meticulous._multiworker import main as multiworker_main
from meticulous._multiworker import show_work_queue
from meticulous._nonword import load_recent_non_words
from meticulous._processrepo import interactive_task_collect_nonwords
from meticulous._storage import get_json_value, prepare, set_json_value
from meticulous._submit import (
    add_change_for_repo,
    fast_prepare_a_pr_or_issue_for,
    prepare_a_pr_or_issue_for,
)
from meticulous._util import get_editor
from meticulous._webserver import main as webserver_main


def get_spelling_store_path(target):
    """
    DB to store spelling stats
    """
    path = target / ".meticulous"
    if not path.is_dir():
        path.mkdir()
    return path / "spelling.db"


def run_invocation(target, start):
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
    init()
    prepare()
    load_recent_non_words(target)
    validate_versions()
    try:
        if start or get_confirmation("Run webserver?"):
            webserver_main(target, start)
        elif get_confirmation("Run automated multi-queue processing?"):
            multiworker_main(target)
        else:
            manual_menu(target)
    except UserCancel:
        print("Quit by user.")


def validate_versions():
    """
    Warn if libraries are old
    """
    versions = [
        ("unanimous", unanimous.version.__version__, "0.6.5"),
        ("spelling", spelling.version.__version__, "0.8.1"),
    ]
    for name, vertxt, minvertxt in versions:
        vertup = tuple(int(elem) for elem in vertxt.split("."))
        minver = tuple(int(elem) for elem in minvertxt.split("."))
        if vertup < minver:
            print(
                f"{Fore.YELLOW}Warning {name} is version"
                f" {vertxt} below minimum of {minvertxt}"
                f"{Style.RESET_ALL}"
            )


def manual_menu(target):
    """
    Present the main menu
    """
    while True:
        try:
            lookup = {
                "automated process": automated_process,
                "automated work queue": multiworker_main,
                "clear work queue": clear_work_queue,
                "show work queue": show_work_queue,
                "examine a repository": examine_repo_selection,
                "manually add a new repository": manually_add_new_repo,
                "remove a repository": remove_repo_selection,
                "add a new repository": add_new_repo,
                "prepare a change": prepare_a_change,
                "prepare a pr/issue": prepare_a_pr_or_issue,
                "total annihilation": total_annihilation,
            }
            handler = make_choice(lookup)
            if handler is None:
                print("Goodbye.")
                return
            handler(target)
        except ProcessingFailed:
            continue


def total_annihilation(target):
    """
    Remove all spelling mistakes from a repository
    """
    reponame, repodir = pick_repo()
    jsonpath = Path(repodir) / "spelling.json"
    if not jsonpath.exists():
        print("Checking spelling...")
        spelling_check(repodir, target)
    interactive_task_collect_nonwords(
        KeyboardInteraction(), reponame, target, nonstop=True
    )


def remove_repo_selection(target):  # pylint: disable=unused-argument
    """
    Select an available repository to remove
    """
    os.chdir(target)
    repo, repodir = pick_repo()
    remove_repo_for(repo, repodir)


def examine_repo_selection(target):  # pylint: disable=unused-argument
    """
    Select an available repository to examine
    """
    _, repodir = pick_repo()
    examine_repo(repodir)


def prepare_a_change(target):  # pylint: disable=unused-argument
    """
    Select an available repository to prepare a change
    """
    _, repodir = pick_repo()
    add_change_for_repo(repodir)


def prepare_a_pr_or_issue(target):  # pylint: disable=unused-argument
    """
    Select an available repository to prepare a change
    """
    reponame, reposave = pick_repo_save()
    prepare_a_pr_or_issue_for(reponame, reposave)


def pick_repo_save():
    """
    Select a saved repository
    """
    return pick_repo_common("repository_saves")


def pick_repo():
    """
    Select an available repository
    """
    return pick_repo_common("repository_map")


def pick_repo_common(key):
    """
    Select an available repository
    """
    repository_list = get_json_value(key, {})
    if not repository_list:
        print("No repositories available.", file=sys.stderr)
        raise NoRepoException()
    option = make_simple_choice(repository_list, "Which Repository?")
    if option is None:
        raise NoRepoException()
    repo_data = repository_list[option]
    return option, repo_data


def examine_repo(repodir):
    """
    Inspect an available repository
    """
    print("Opening editor")
    editor = local[get_editor()]
    # plumbum bug workaround
    os.chdir(pathlib.Path.home())
    with local.cwd(repodir):
        _ = editor["spelling.txt"] & FG


def manually_add_new_repo(target):
    """
    Allow entry of a new repository manually
    """
    choices = sorted(os.listdir(target))
    option = make_simple_choice(choices, "Which Directory?")
    if option is None:
        raise NoRepoException()
    repository_map = get_json_value("repository_map", {})
    repository_map[option] = str(Path(target) / option)
    set_json_value("repository_map", repository_map)


def add_new_repo(target):
    """
    Query how many new repositories and add them
    """
    choices = {str(num).zfill(2): str(num) for num in (1, 2, 5, 10, 20)}
    option = make_simple_choice(choices, "How Many?")
    if option is None:
        return
    for _ in range(int(option)):
        interactive_add_one_new_repo(target)


def automated_process(target):  # pylint: disable=unused-argument
    """
    Work out the current point in the automated workflow and process the next
    step.
    """
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace(
        [task_add_repo, task_collect_nonwords, task_submit, task_cleanup]
    )
    my_engine.process([State(target)])


class State:  # pylint: disable=too-few-public-methods
    """
    Store the workflow state.
    """

    def __init__(self, target):
        self.target = target


def task_add_repo(obj, eng):  # pylint: disable=unused-argument
    """
    Ensures a repo has been forked.
    """
    key = "repository_map"
    repository_list = get_json_value(key, {})
    if not repository_list:
        interactive_add_one_new_repo(obj.target)


def task_collect_nonwords(obj, eng):  # pylint: disable=unused-argument
    """
    Saves nonwords until a typo is found
    """
    key = "repository_map"
    repository_list = get_json_value(key, {})
    count = len(repository_list)
    if count < 1:
        print(f"Unexpected number of repostories - {count}")
        return
    reponame = next(iter(repository_list.keys()))
    interactive_task_collect_nonwords(
        KeyboardInteraction(), reponame, obj.target, nonstop=ALWAYS_BATCH_MODE
    )


def task_submit(obj, eng):  # pylint: disable=unused-argument
    """
    Submits the typo
    """
    repository_saves = get_json_value("repository_saves", {})
    count = len(repository_saves)
    if count < 1:
        print(f"Unexpected number of repostories - {count}")
        return
    reponame, reposave = next(iter(repository_saves.items()))
    fast_prepare_a_pr_or_issue_for(reponame, reposave)


def task_cleanup(obj, eng):  # pylint: disable=unused-argument
    """
    Submits the typo
    """
    key = "repository_map"
    repository_map = get_json_value(key, {})
    count = len(repository_map)
    if count < 1:
        print(f"Unexpected number of repostories - {count}")
        return
    reponame, reposave = next(iter(repository_map.items()))
    remove_repo_for(reponame, reposave, confirm=False)
