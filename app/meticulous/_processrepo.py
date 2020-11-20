"""
Work through nonwords to find a typo
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

from meticulous._nonword import (
    add_non_word,
    check_nonwords,
    is_local_non_word,
    update_nonwords,
)
from meticulous._storage import get_json_value, set_json_value
from meticulous._util import get_browser
from meticulous._websearch import Suggestion


class NonwordState:  # pylint: disable=too-few-public-methods
    """
    Store the nonword workflow state.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self, context, target, word, details, repopath, nonword_delegate
    ):
        self.context = context
        self.target = target
        self.word = word
        self.details = details
        self.repopath = repopath
        self.nonword_delegate = nonword_delegate
        self.done = False


def processrepo_handlers():
    """
    Add handlers for processing a repository
    """
    return {"collect_nonwords": collect_nonwords, "nonword_update": nonword_update}


def collect_nonwords(context):
    """
    Task to collect nonwords from a repository until a typo is found or the
    repository is clean
    """

    def handler():
        target = context.controller.target
        reponame = context.taskjson["reponame"]
        if reponame in get_json_value("repository_map", {}):
            interactive_task_collect_nonwords(
                context,
                reponame,
                target,
                nonword_delegate=noninteractive_nonword_delegate(context),
            )
        context.controller.add(
            {
                "name": "repository_summary",
                "interactive": True,
                "priority": 55,
                "reponame": reponame,
            }
        )

    return handler


def nonword_update(context):
    """
    Task to push nonwords upstream
    """

    def handler():
        target = context.controller.target
        update_nonwords(target)

    return handler


def noninteractive_nonword_delegate(context):
    """
    Obtain a basic interactive nonword update
    """

    def handler():
        context.controller.add({"name": "nonword_update", "interactive": False})

    return handler


def interactive_nonword_delegate(context, target):
    """
    Obtain a basic interactive nonword update
    """

    def handler():
        pullreq = update_nonwords(target)
        context.interactive.send(
            f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}"
        )

    return handler


def interactive_task_collect_nonwords(  # pylint: disable=unused-argument
    context, reponame, target, nonword_delegate=None, nonstop=False
):
    """
    Saves nonwords until a typo is found
    """
    if nonword_delegate is None:
        nonword_delegate = interactive_nonword_delegate(context, target)
    key = "repository_map"
    repository_map = get_json_value(key, {})
    repodir = repository_map[reponame]
    repodirpath = Path(repodir)
    jsonpath = repodirpath / "spelling.json"
    if not jsonpath.is_file():
        context.interaction.send(f"Unable to locate spelling at {jsonpath}")
        return
    with io.open(jsonpath, "r", encoding="utf-8") as fobj:
        jsonobj = json.load(fobj)
    complete = interactive_task_collect_nonwords_run(
        context, repodirpath, target, nonstop, nonword_delegate, jsonobj
    )
    if complete:
        context.interaction.send(
            f"{Fore.YELLOW}Completed checking all"
            f" words for {reponame}!{Style.RESET_ALL}"
        )


def interactive_task_collect_nonwords_run(
    context, repodirpath, target, nonstop, nonword_delegate, jsonobj
):
    """
    Given the json state - saves nonwords until a typo is found
    """
    words = get_sorted_words(context.interaction, jsonobj)
    if not words:
        return True
    processrepo = context.interaction.get_confirmation(
        "Do you want to process this repository?", defaultval=True
    )
    if not processrepo:
        return False
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace([check_websearch, is_nonword, is_typo, what_now])
    for word in words:
        state = NonwordState(
            context=context,
            target=target,
            word=word,
            details=jsonobj[word],
            repopath=repodirpath,
            nonword_delegate=nonword_delegate,
        )
        try:
            my_engine.process([state])
        except HaltProcessing:
            if state.done and not nonstop:
                return False
    return True


def get_sorted_words(interaction, jsonobj):
    """
    Sort the words first by frequency
    """
    order = []
    for word, details in jsonobj.items():
        if is_local_non_word(word):
            continue
        priority = 0
        replacement = ""
        if details.get("suggestion"):
            obj = Suggestion.load(details["suggestion"])
            details["suggestion_obj"] = obj
            priority = obj.priority
            replacement = obj.replacement
        order.append(((priority, len(details["files"]), replacement), word))
    order.sort(reverse=True)
    interaction.send(f"-- Candidates Found: {len(order)} --")
    maxwords = 50
    for (priority, num_files, replacement), word in order[:maxwords]:
        if not replacement:
            replacement = "?"
        interaction.send(f"{word} (-> {replacement} # files: {num_files})")
    if len(order) > maxwords:
        interaction.send(f"-- Skipping {len(order) - maxwords} candidates. --")
    else:
        interaction.send("-- End of candidates. --")
    return [word for _, word in order]


def check_websearch(obj, eng):
    """
    Quick initial check to see if a websearch provides a suggestion.
    """
    suggestion = obj.details.get("suggestion_obj")
    if suggestion is None:
        return
    show_word(obj.context.interaction, obj.word, obj.details)
    if suggestion.is_nonword:
        is_non_word_check = obj.context.interaction.get_confirmation(
            "Web search suggests it is a non-word, agree?"
        )
        if is_non_word_check:
            handle_nonword(obj.word, obj.target, obj.nonword_delegate)
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
            obj.context.interaction.send(msgs[-1])
            suggestion_check = obj.context.interaction.get_confirmation(
                msgs[0], defaultval=False
            )
            if suggestion_check:
                fix_word(
                    obj.context.interaction,
                    obj.word,
                    obj.details,
                    suggestion.replacement,
                    obj.repopath,
                )
                obj.done = True
                eng.halt("found typo")
        msgs = [
            (f"Web search suggests using {prefix}" f"typo{suffix}, agree?")
            for prefix, suffix in [("", ""), (Fore.RED, Style.RESET_ALL)]
        ]
        obj.context.interaction.send(msgs[-1])
        last_suggestion_check = obj.context.interaction.get_confirmation(
            msgs[0], defaultval=False
        )
        if last_suggestion_check:
            handle_typo(obj.context.interaction, obj.word, obj.details, obj.repopath)
            obj.done = True
            eng.halt("found typo")


def is_nonword(obj, eng):
    """
    Quick initial check to see if it is a nonword.
    """
    show_word(obj.context.interaction, obj.word, obj.details)
    if obj.context.interaction.get_confirmation("Is non-word?"):
        handle_nonword(obj.word, obj.target, obj.nonword_delegate)
        eng.halt("found nonword")


def is_typo(obj, eng):
    """
    Quick initial check to see if it is a typo.
    """
    show_word(obj.context.interaction, obj.word, obj.details)
    if obj.context.interaction.get_confirmation("Is it typo?"):
        handle_typo(obj.context.interaction, obj.word, obj.details, obj.repopath)
        obj.done = True
        eng.halt("found typo")


def what_now(obj, eng):
    """
    Check to see what else to do.
    """
    show_word(obj.context.interaction, obj.word, obj.details)
    obj.context.interaction.send("Todo what now options?")
    eng.halt("what now?")


def show_word(interaction, word, details):  # pylint: disable=unused-argument
    """
    Display the word and its context.
    """
    files = sorted(
        set(context_to_filename(detail["file"]) for detail in details["files"])
    )
    interaction.send(f"Checking word {word} - ({len(files)} files)")
    max_files = 4
    for filename in files[:max_files]:
        interaction.send(f"{filename}:")
        with io.open(filename, "r", encoding="utf-8") as fobj:
            show_next = False
            prev_line = None
            shown = 0
            max_shown = 3
            for line in fobj:
                line = line.rstrip("\r\n")
                output = get_colourized(line, word)
                if output:
                    if shown < max_shown:
                        if prev_line:
                            interaction.send("-" * 60)
                            interaction.send(prev_line)
                            prev_line = None
                        interaction.send(output)
                        show_next = True
                    else:
                        shown += 1
                elif show_next:
                    interaction.send(line)
                    interaction.send("-" * 60)
                    show_next = False
                    shown += 1
                else:
                    prev_line = line
            if shown > max_shown:
                interaction.send(f"... (skipping {shown - max_shown} matches)")
    if len(files) > max_files:
        interaction.send(f"... (skipping {len(files) - max_files} files)")


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


def handle_nonword(word, target, nonword_delegate):  # pylint: disable=unused-argument
    """
    Handle a nonword
    """
    add_non_word(word, target)
    if check_nonwords(target):
        nonword_delegate()


def handle_typo(
    interaction, word, details, repopath
):  # pylint: disable=unused-argument
    """
    Handle a typo
    """
    if interaction.get_confirmation(f"Do you want to google {word}"):
        browser = local[get_browser()]
        search = f"https://www.google.com.au/search?q={quote(word)}"
        _ = browser[search] & FG
    newspell = interaction.get_input(f"How do you spell {word}?")
    if newspell:
        fix_word(interaction, word, details, newspell, repopath)


def fix_word(interaction, word, details, newspell, repopath):
    """
    Save the correction
    """
    interaction.send(f"Changing {word} to {newspell}")
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
