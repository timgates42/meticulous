"""
Load, save and pass off handling to the controller
"""

import io
import json
import re
from pathlib import Path
from urllib.parse import quote

from colorama import Fore, Style
from plumbum import FG, local
from spelling.check import context_to_filename
from workflow.engine import GenericWorkflowEngine
from workflow.errors import HaltProcessing

from meticulous._addrepo import interactive_add_one_new_repo
from meticulous._controller import Controller
from meticulous._input import get_confirmation, get_input
from meticulous._input_queue import get_input_queue
from meticulous._nonword import (
    add_non_word,
    check_nonwords,
    is_local_non_word,
    update_nonwords,
)
from meticulous._storage import get_json_value, set_json_value
from meticulous._threadpool import get_pool
from meticulous._util import get_browser
from meticulous._websearch import Suggestion


class NonwordState:  # pylint: disable=too-few-public-methods
    """
    Store the nonword workflow state.
    """

    def __init__(self, target, word, details, repopath):
        self.target = target
        self.word = word
        self.details = details
        self.repopath = repopath
        self.done = False


def update_workload(workload):
    """
    Ensure the minimum number of repository tasks are present.
    """
    result = list(workload)
    load_count = count_names(workload, {"repository_load"})
    active_count = len(get_json_value("repository_map", {}))
    for _ in range(1 - active_count - load_count):
        result.append({"interactive": True, "name": "repository_load", "priority": 60})
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


def repository_load(context):
    """
    Task to pull a repository
    """

    def handler():
        target = context.controller.target
        reponame = interactive_add_one_new_repo(target)
        context.controller.add(
            {
                "name": "collect_nonwords",
                "interactive": True,
                "priority": 50,
                "reponame": reponame,
            }
        )
        print("completed processing")
        context.controller.quit()

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


def interactive_task_collect_nonwords(  # pylint: disable=unused-argument
    reponame, target
):
    """
    Saves nonwords until a typo is found
    """
    key = "repository_map"
    repository_map = get_json_value(key, {})
    repodir = repository_map[reponame]
    repodirpath = Path(repodir)
    jsonpath = repodirpath / "spelling.json"
    with io.open(jsonpath, "r", encoding="utf-8") as fobj:
        jsonobj = json.load(fobj)
    words = get_sorted_words(jsonobj)
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace([check_websearch, is_nonword, is_typo, what_now])
    for word in words:
        state = NonwordState(
            target=target, word=word, details=jsonobj[word], repopath=repodirpath
        )
        try:
            my_engine.process([state])
        except HaltProcessing:
            if state.done:
                return
    print(f"{Fore.YELLOW}Completed checking all words!{Style.RESET_ALL}")


def get_sorted_words(jsonobj):
    """
    Sort the words first by frequency
    """
    order = []
    for word, details in jsonobj.items():
        if is_local_non_word(word):
            continue
        priority = 0
        if details.get("suggestion"):
            obj = Suggestion.load(details["suggestion"])
            details["suggestion_obj"] = obj
            priority = obj.priority
        order.append(((priority, len(details["files"])), word))
    order.sort(reverse=True)
    return [word for _, word in order]


def check_websearch(obj, eng):
    """
    Quick initial check to see if a websearch provides a suggestion.
    """
    suggestion = obj.details.get("suggestion_obj")
    if suggestion is None:
        return
    show_word(obj.word, obj.details)
    if suggestion.is_nonword:
        if get_confirmation("Web search suggests it is a non-word, agree?"):
            handle_nonword(obj.word, obj.target)
            eng.halt("found nonword")
    if suggestion.is_typo:
        if suggestion.replacement:
            msgs = [
                (
                    f"Web search suggests using {prefix}"
                    f"{suggestion.replacement}{suffix}, agree?"
                )
                for prefix, suffix in [("", ""), (Fore.CYAN, Style.RESET_ALL)]
            ]
            print(msgs[-1])
            if get_confirmation(msgs[0], defaultval=False):
                fix_word(obj.word, obj.details, suggestion.replacement, obj.repopath)
                obj.done = True
                eng.halt("found typo")
        msgs = [
            (f"Web search suggests using {prefix}" f"typo{suffix}, agree?")
            for prefix, suffix in [("", ""), (Fore.RED, Style.RESET_ALL)]
        ]
        print(msgs[-1])
        if get_confirmation(msgs[0], defaultval=False):
            handle_typo(obj.word, obj.details, obj.repopath)
            obj.done = True
            eng.halt("found typo")


def is_nonword(obj, eng):
    """
    Quick initial check to see if it is a nonword.
    """
    show_word(obj.word, obj.details)
    if get_confirmation("Is non-word?"):
        handle_nonword(obj.word, obj.target)
        eng.halt("found nonword")


def is_typo(obj, eng):
    """
    Quick initial check to see if it is a typo.
    """
    show_word(obj.word, obj.details)
    if get_confirmation("Is it typo?"):
        handle_typo(obj.word, obj.details, obj.repopath)
        obj.done = True
        eng.halt("found typo")


def what_now(obj, eng):
    """
    Check to see what else to do.
    """
    show_word(obj.word, obj.details)
    print("Todo what now options?")
    eng.halt("what now?")


def show_word(word, details):  # pylint: disable=unused-argument
    """
    Display the word and its context.
    """
    print(f"Checking word {word}")
    files = sorted(
        set(context_to_filename(detail["file"]) for detail in details["files"])
    )
    for filename in files:
        print(f"{filename}:")
        with io.open(filename, "r", encoding="utf-8") as fobj:
            show_next = False
            prev_line = None
            for line in fobj:
                line = line.rstrip("\r\n")
                output = get_colourized(line, word)
                if output:
                    if prev_line:
                        print("-" * 60)
                        print(prev_line)
                        prev_line = None
                    print(output)
                    show_next = True
                elif show_next:
                    print(line)
                    print("-" * 60)
                    show_next = False
                else:
                    prev_line = line


def get_colourized(line, word):
    """
    Highlight the matching word for lines it is found on.
    """
    replacement = "".join([Fore.YELLOW, word, Style.RESET_ALL])
    return perform_replacement(line, word, replacement)


def perform_replacement(line, word, replacement):
    """
    Run the provided word replacement
    """
    regex = re.compile(f"\\b({re.escape(word)})\\b")
    if not regex.search(line):
        return None
    result = []
    pos = 0
    for match in regex.finditer(line):
        match_start = match.start(1)
        match_end = match.end(1)
        result.append(line[pos:match_start])
        result.append(replacement)
        pos = match_end
    result.append(line[pos:])
    return "".join(result)


def handle_nonword(word, target):  # pylint: disable=unused-argument
    """
    Handle a nonword
    """
    add_non_word(word, target)
    if check_nonwords(target):
        pullreq = update_nonwords(target)
        print(f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}")


def handle_typo(word, details, repopath):  # pylint: disable=unused-argument
    """
    Handle a typo
    """
    if get_confirmation(f"Do you want to google {word}"):
        browser = local[get_browser()]
        search = f"https://www.google.com.au/search?q={quote(word)}"
        _ = browser[search] & FG
    newspell = get_input(f"How do you spell {word}?")
    if newspell:
        fix_word(word, details, newspell, repopath)


def fix_word(word, details, newspell, repopath):
    """
    Save the correction
    """
    print(f"Changing {word} to {newspell}")
    files = sorted(
        set(context_to_filename(detail["file"]) for detail in details["files"])
    )
    file_paths = []
    for filename in files:
        lines = []
        with io.open(filename, "r", encoding="utf-8") as fobj:
            for line in fobj:
                line = line.rstrip("\r\n")
                output = perform_replacement(line, word, newspell)
                lines.append(output if output is not None else line)
        with io.open(filename, "w", encoding="utf-8") as fobj:
            for line in lines:
                print(line, file=fobj)
        git = local["git"]
        filepath = Path(filename)
        relpath = str(filepath.relative_to(repopath))
        with local.cwd(str(repopath)):
            _ = git["add"][relpath] & FG
        file_paths.append(relpath)
    add_repo_save(str(repopath), newspell, word, file_paths)


def add_repo_save(repodir, add_word, del_word, file_paths):
    """
    Record a typo correction
    """
    saves = get_json_value("repository_saves", {})
    reponame = Path(repodir).name
    saves[reponame] = {
        "add_word": add_word,
        "del_word": del_word,
        "file_paths": file_paths,
        "repodir": repodir,
    }
    set_json_value("repository_saves", saves)


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
