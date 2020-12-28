"""
Manage process of adding repositories
"""

import io
import json
import random
import subprocess  # noqa=S404 # nosec
import sys
import threading

import unanimous
from github import GithubException

from meticulous._github import (
    check_forked,
    checkout,
    fork,
    get_true_orgrepo,
    is_archived,
    issues_allowed,
)
from meticulous._nonword import is_local_non_word
from meticulous._progress import add_progress, clear_progress
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, set_json_value
from meticulous._summary import display_repo_intro
from meticulous._websearch import get_suggestion

LOCK = threading.Lock()


def addrepo_handlers():
    """
    Get multiqueue task handlers for adding a repository
    """
    return {
        "repository_load": repository_load,
        "repository_checkout": repository_checkout,
        "repository_summary": repository_summary,
        "repository_end": repository_end,
    }


def repository_load(context):
    """
    Task to pull a repository
    """

    def handler():
        reponame = non_interactive_pickrepo()
        if reponame is None:
            context.controller.add(
                {"name": "repository_end", "interactive": True, "priority": 65}
            )
        else:
            context.controller.add(
                {
                    "name": "repository_checkout",
                    "interactive": False,
                    "reponame": reponame,
                }
            )

    return handler


def repository_checkout(context):
    """
    Task to pull a repository
    """

    def handler():
        target = context.controller.target
        reponame = context.taskjson["reponame"]
        noninteractive_checkout(target, reponame)
        context.controller.add(
            {
                "name": "repository_summary",
                "interactive": True,
                "priority": 55,
                "reponame": reponame,
            }
        )

    return handler


def repository_end(context):
    """
    Report exhaustion of source repositories
    """

    def handler():
        context.interaction.send("No more repositories")
        context.interaction.get_confirmation("Enjoy meticulous?")
        context.controller.quit()
    return handler


def repository_summary(context):
    """
    Task to pull a repository
    """

    def handler():
        target = context.controller.target
        reponame = context.taskjson["reponame"]
        repodir = target / reponame
        repository_map = get_json_value("repository_map", {})
        repository_map[reponame] = str(repodir)
        set_json_value("repository_map", repository_map)
        display_repo_intro(repodir)
        context.controller.add(
            {
                "name": "collect_nonwords",
                "interactive": True,
                "priority": 50,
                "reponame": reponame,
            }
        )
        if context.interaction.check_quit(context.controller):
            context.controller.quit()

    return handler


def interactive_add_one_new_repo(target):
    """
    Locate a new repository and add it to the available set.
    """
    repo = non_interactive_pickrepo()
    if repo is None:
        return None
    noninteractive_checkout(target, repo)
    repodir = target / repo
    display_repo_intro(repodir)
    return repo


def noninteractive_checkout(target, repo):
    """
    Handle obtaining and spell checking repo
    """
    print(f"Checkout {repo}")
    checkout(repo, target)
    print(f"Checking {repo}")
    spelling_check(repo, target)
    print(f"Completed checking {repo}")
    return repo


def non_interactive_pickrepo():
    """
    Select next free repo
    """
    forking = []
    return_repo = None
    with LOCK:
        repository_forked = get_json_value("repository_forked", {})
        for orgrepo in obtain_sources():
            _, origrepo = orgrepo.split("/", 1)
            if origrepo in repository_forked:
                continue
            try:
                orgrepo = get_true_orgrepo(orgrepo)
            except GithubException:
                continue
            _, repo = orgrepo.split("/", 1)
            if repo in repository_forked:
                continue
            if check_forked(orgrepo):
                repository_forked[origrepo] = True
                repository_forked[repo] = True
                set_json_value("repository_forked", repository_forked)
                continue
            forking.append(orgrepo)
            if is_archived(orgrepo):
                repository_forked[origrepo] = True
                repository_forked[repo] = True
                set_json_value("repository_forked", repository_forked)
                continue
            repository_forked[origrepo] = True
            repository_forked[repo] = True
            set_json_value("repository_forked", repository_forked)
            return_repo = repo
            break
    for orgrepo in forking:
        fork(orgrepo)
    return return_repo


def spelling_check(repo, target):
    """
    Run the spelling check on the target repo.
    """
    repodir = target / repo
    jsonpath = repodir / "spelling.json"
    procobj = subprocess.Popen(  # noqa=S603 # nosec
        [
            sys.executable,
            "-m",
            "spelling",
            "--no-display-context",
            "--no-display-summary",
            "--working-path",
            str(repodir),
            "--json-path",
            str(jsonpath),
        ],
        stdout=subprocess.PIPE,
        stdin=None,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = procobj.communicate()
    if procobj.returncode not in (0, 1):
        raise Exception(f"Error checking spelling:\n{stderr}\n{stdout}")
    with io.open(jsonpath, "r", encoding="utf-8") as fobj:
        jsonobj = json.load(fobj)
    jsonobj = update_json_results(repo, jsonobj)
    with io.open(jsonpath, "w", encoding="utf-8") as fobj:
        json.dump(jsonobj, fobj)
    if not issues_allowed(repo):
        no_issues_path = repodir / "__no_issues__.txt"
        with io.open(no_issues_path, "w", encoding="utf-8") as fobj:
            print("No Issues.", file=fobj)


def update_json_results(repo, words):
    """
    Add suggestions for words
    """
    key = ("suggestions", repo)
    result = {}
    items = list(words.items())
    random.SystemRandom().shuffle(items)
    count = 0
    max_suggestions = 50
    for index, (word, details) in enumerate(items):
        add_progress(key, f"Processing {index + 1} of {len(items)} for {repo}")
        if unanimous.util.is_nonword(word):
            details["nonword"] = True
            continue
        if is_local_non_word(word):
            details["nonword"] = True
            continue
        if count < max_suggestions:
            suggestion = get_suggestion(word)
            count += 1
            if suggestion is not None:
                details["suggestion"] = suggestion.save()
        result[word] = details
    clear_progress(key)
    return result
