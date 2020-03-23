"""
Load, save and pass off handling to the controller
"""

import io
import json
import subprocess  # noqa=S404 # nosec
import sys

import unanimous

from meticulous._controller import Controller
from meticulous._github import (
    check_forked,
    checkout,
    fork,
    get_true_orgrepo,
    is_archived,
    issues_allowed,
)
from meticulous._input import get_confirmation
from meticulous._input_queue import get_input_queue
from meticulous._nonword import is_local_non_word
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, set_json_value
from meticulous._summary import display_repo_intro
from meticulous._threadpool import get_pool
from meticulous._websearch import get_suggestion


def update_workload(workload):
    """
    Ensure the minimum number of repository tasks are present.
    """
    result = list(workload)
    load_count = count_names(workload, {"repository_load"})
    for _ in range(3 - load_count):
        result.append({"interactive": False, "name": "repository_load"})
    if count_names(workload, {"wait_threadpool"}) < 1:
        result.append({"interactive": True, "name": "wait_threadpool", "priority": 999})
    if count_names(workload, {"force_quit"}) < 1:
        result.append({"interactive": True, "name": "force_quit", "priority": 1000})
    return result


def count_names(workload, names):
    """
    Get the number of tasks matching the name collection
    """
    count = 0
    for elem in workload:
        if elem["name"] in names:
            count += 1
    return count


def get_handlers():
    """
    Obtain the handler factory lookup
    """
    return {
        "repository_load": repository_load,
        "prompt_quit": prompt_quit,
        "wait_threadpool": wait_threadpool,
        "force_quit": force_quit,
    }


def repository_load(_):
    """
    Task to pull a repository
    """

    def handler():
        pass

    return handler


def wait_threadpool(context):
    """
    Wait until all an input task is added to the queue or all tasks have
    completed processing.
    """

    def handler():
        with context.controller.condition:
            while True:
                tasks_empty = context.controller.tasks_empty()
                top = context.controller.peek_input()
                if top["priority"] < 999:
                    context.controller.add(
                        {
                            "interactive": True,
                            "name": "wait_threadpool",
                            "priority": 999,
                        }
                    )
                    return
                if tasks_empty:
                    print("All tasks complete and no new input - quiting.")
                    context.controller.quit()
                    return
                context.controller.condition.wait(60)

    return handler


def prompt_quit(context):
    """
    Interactive request to quit
    """

    def handler():
        if get_confirmation(message="Do you want to quit?", defaultval=True):
            context.controller.quit()

    return handler


def force_quit(context):
    """
    Force quit
    """

    def handler():
        context.controller.quit()

    return handler


def interactive_add_one_new_repo(target):
    """
    Locate a new repository and add it to the available set.
    """
    repository_forked = get_json_value("repository_forked", {})
    for orgrepo in obtain_sources():
        _, origrepo = orgrepo.split("/", 1)
        if origrepo in repository_forked:
            continue
        orgrepo = get_true_orgrepo(orgrepo)
        _, repo = orgrepo.split("/", 1)
        if repo in repository_forked:
            continue
        print(f"Checking {orgrepo}")
        if check_forked(orgrepo):
            repository_forked[origrepo] = True
            repository_forked[repo] = True
            set_json_value("repository_forked", repository_forked)
            continue
        print(f"Have not forked {orgrepo}")
        print(f"Forking {orgrepo}")
        fork(orgrepo)
        if is_archived(orgrepo):
            print(f"Skipping archived repo {orgrepo}")
            repository_forked[origrepo] = True
            repository_forked[repo] = True
            set_json_value("repository_forked", repository_forked)
            continue
        print(f"Checkout {repo}")
        checkout(repo, target)
        spelling_check(repo, target)
        repository_forked[origrepo] = True
        repository_forked[repo] = True
        set_json_value("repository_forked", repository_forked)
        return repo
    return None


def spelling_check(repo, target):
    """
    Run the spelling check on the target repo.
    """
    repodir = target / repo
    print(f"Running spell check on {repodir}")
    spellpath = repodir / "spelling.txt"
    print(f"Spelling output {spellpath}")
    display_repo_intro(repodir)
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
    jsonobj = update_json_results(jsonobj)
    with io.open(jsonpath, "w", encoding="utf-8") as fobj:
        json.dump(jsonobj, fobj)
    repository_map = get_json_value("repository_map", {})
    repository_map[repo] = str(repodir)
    set_json_value("repository_map", repository_map)
    if not issues_allowed(repo):
        no_issues_path = repodir / "__no_issues__.txt"
        with io.open(no_issues_path, "w", encoding="utf-8") as fobj:
            print("No Issues.", file=fobj)


def update_json_results(words):
    """
    Add suggestions for words
    """
    result = {}
    for word, details in words.items():
        if unanimous.util.is_nonword(word):
            details["nonword"] = True
            continue
        if is_local_non_word(word):
            details["nonword"] = True
            continue
        suggestion = get_suggestion(word)
        if suggestion is not None:
            details["suggestion"] = suggestion.save()
        result[word] = details
    return result


def main(target):
    """
    Main task should load from storage, update the workload and pass off
    handling to the controller and on termination save the result
    """
    key = "multiworker_workload"
    workload = get_json_value(key, deflt=[])
    workload = update_workload(workload)
    handlers = get_handlers()
    input_queue = get_input_queue()
    threadpool = get_pool(handlers)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool, target=target
    )
    for task in workload:
        controller.add(task)
    result = controller.run()
    set_json_value(key, result)
