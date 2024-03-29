"""
Work through nonwords to find a typo
"""

import collections
import io
import json
import logging
import os
import pathlib
import re
from pathlib import Path

from colorama import Fore, Style
from plumbum import FG, ProcessExecutionError, local
from spelling.check import context_to_filename
from workflow.engine import GenericWorkflowEngine
from workflow.errors import HaltProcessing

from meticulous._constants import ALWAYS_BATCH_MODE
from meticulous._nonword import (
    add_non_word,
    check_nonwords,
    is_local_non_word,
    update_nonwords,
)
from meticulous._storage import get_json_value, get_multi_repo, set_multi_repo
from meticulous._websearch import Suggestion


class NonwordState:  # pylint: disable=too-few-public-methods
    """
    Store the nonword workflow state.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self, interaction, target, word, details, repopath, nonword_delegate
    ):
        self.interaction = interaction
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
                context.interaction,
                reponame,
                target,
                nonword_delegate=noninteractive_nonword_delegate(context),
                nonstop=ALWAYS_BATCH_MODE,
            )
            context.controller.add(
                {
                    "name": "submit",
                    "interactive": True,
                    "priority": 50,
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


def interactive_nonword_delegate(interaction, target):
    """
    Obtain a basic interactive nonword update
    """

    def handler():
        pullreq = update_nonwords(target)
        interaction.send(f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}")

    return handler


def interactive_task_collect_nonwords(  # pylint: disable=unused-argument
    interaction, reponame, target, nonword_delegate=None, nonstop=False
):
    """
    Saves nonwords until a typo is found
    """
    if nonword_delegate is None:
        nonword_delegate = interactive_nonword_delegate(interaction, target)
    key = "repository_map"
    repository_map = get_json_value(key, {})
    repodir = repository_map[reponame]
    repodirpath = Path(repodir)
    jsonpath = repodirpath / "spelling.json"
    if not jsonpath.is_file():
        interaction.send(f"Unable to locate spelling at {jsonpath}")
        return
    with io.open(jsonpath, "r", encoding="utf-8") as fobj:
        jsonobj = json.load(fobj)
    state = NonwordState(
        interaction=interaction,
        target=target,
        word=None,
        details=None,
        repopath=repodirpath,
        nonword_delegate=nonword_delegate,
    )
    completed = interactive_task_collect_nonwords_run(state, nonstop, jsonobj)
    if completed:
        interaction.send(
            f"{Fore.YELLOW}Found all words" f" for {reponame}!{Style.RESET_ALL}"
        )


def interactive_task_collect_nonwords_run(state, nonstop, jsonobj):
    """
    Given the json state - saves nonwords until a typo is found
    """
    wordchoice = get_sorted_words(state.interaction, jsonobj)
    handler = WordChoiceHandler(wordchoice)
    return handler.run(
        state,
        nonstop,
        jsonobj,
    )


WordChoiceResult = collections.namedtuple(
    "WordChoiceResult", ["skip", "completed", "force_completed"]
)


class WordChoiceHandler:
    """
    State for picking a word from a selection
    """

    def __init__(self, wordchoice):
        self.wordchoice = wordchoice

    def run(self, state, nonstop, jsonobj):
        """
        Main word selection handler.
        """
        print("selecting words")
        while self.wordchoice:
            result = self.select(state, jsonobj)
            if result.force_completed:
                break
            if result.completed and not nonstop:
                return False
            if result.skip:
                return False
        print("selecting words completed")
        state.interaction.complete_repo()
        return True

    def select(self, state, jsonobj):
        """
        Provide a selection of options for choice
        """
        choices = self.get_choices(state, jsonobj)
        print(f"make choice {len(choices)}")
        handler = state.interaction.make_choice(choices)
        return handler()

    def get_choices(self, state, jsonobj):
        """
        Prepare the list of options
        """

        def complete_handler():
            """
            Finish processing
            """
            return WordChoiceResult(skip=False, completed=True, force_completed=True)

        def skip_handler():
            """
            Finish processing early
            """
            return WordChoiceResult(skip=True, completed=False, force_completed=False)

        ctxt = "98) Complete repository."
        stxt = "99) Skip repository."
        choices = {ctxt: complete_handler, stxt: skip_handler}
        for txt, word in self.wordchoice:
            choices[txt] = WordHandler(self, word, state, jsonobj)
        return choices

    def remove(self, word):
        """
        Given a word to drop from the selection locate it and remove it
        """
        for index, txtword in enumerate(self.wordchoice):
            if txtword[0] == word:
                del self.wordchoice[index]
                return


class WordHandler:  # pylint: disable=too-few-public-methods
    """
    Action to take if a word is selected
    """

    def __init__(
        self,
        choicehandler,
        word,
        state,
        jsonobj,
    ):
        self.choicehandler = choicehandler
        self.word = word
        self.state = state
        self.jsonobj = jsonobj

    def __call__(self):
        completed = interactive_new_word(
            self.state,
            self.jsonobj,
            self.word,
        )
        self.choicehandler.remove(self.word)
        return WordChoiceResult(skip=False, completed=completed, force_completed=False)


def gen_fix_word(interaction, word, details, replacement, repopath):
    """
    Create call delegate for fix_word
    """

    def call_fix_word():
        """
        The call delegate for fix_word
        """
        return fix_word(interaction, word, details, replacement, repopath)

    return call_fix_word


def interactive_new_word(state, jsonobj, word):
    """
    Single word processing
    """
    details = jsonobj[word]
    suggestion = details.get("suggestion_obj")
    show_word(state.interaction, word, details)

    def nonword_call():
        """
        Selected nonword option
        """
        return handle_nonword(word, state.target, state.nonword_delegate)

    choices = {
        "1) Typo": lambda: (
            handle_typo(state.interaction, word, details, state.repopath)
        ),
        "2) Non-word": nonword_call,
        "3) Skip": lambda: False,
    }
    if suggestion is not None:
        if suggestion.is_nonword:
            text = "0) Suggest non-word, agree?"
            choices[text] = nonword_call
        if suggestion.is_typo:
            if suggestion.replacement_list:
                for index, replacement in enumerate(suggestion.replacement_list):
                    numtxt = str(index).zfill(3)
                    text = f"{numtxt}) Suggest using {replacement}, agree?"
                    choices[text] = gen_fix_word(
                        state.interaction,
                        word,
                        details,
                        replacement,
                        state.repopath,
                    )
    result = state.interaction.make_choice(choices)
    return result()


def interactive_old_word(state, jsonobj, word):
    """
    Single word processing
    """
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace([check_websearch, is_nonword, is_typo, what_now])
    newstate = NonwordState(
        interaction=state.interaction,
        target=state.target,
        word=word,
        details=jsonobj[word],
        repopath=state.repopath,
        nonword_delegate=state.nonword_delegate,
    )
    try:
        my_engine.process([newstate])
    except HaltProcessing:
        if newstate.done:
            return True
    return False


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
    wordchoice = []
    for num, ((priority, num_files, replacement), word) in enumerate(order[:maxwords]):
        if not replacement:
            replacement = "?"
        txt = f"{str(num).zfill(2)}) {word} (-> {replacement} # files: {num_files})"
        interaction.send(txt)
        wordchoice.append((txt, word))
    if len(order) > maxwords:
        interaction.send(f"-- Skipping {len(order) - maxwords} candidates. --")
    else:
        interaction.send("-- End of candidates. --")
    return wordchoice


def check_websearch(obj, eng):
    """
    Quick initial check to see if a websearch provides a suggestion.
    """
    suggestion = obj.details.get("suggestion_obj")
    if suggestion is None:
        return
    show_word(obj.interaction, obj.word, obj.details)
    if suggestion.is_nonword:
        is_non_word_check = obj.interaction.get_confirmation(
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
            obj.interaction.send(msgs[-1])
            suggestion_check = obj.interaction.get_confirmation(
                msgs[0], defaultval=False
            )
            if suggestion_check:
                fix_word(
                    obj.interaction,
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
        obj.interaction.send(msgs[-1])
        last_suggestion_check = obj.interaction.get_confirmation(
            msgs[0], defaultval=False
        )
        if last_suggestion_check:
            handle_typo(obj.interaction, obj.word, obj.details, obj.repopath)
            obj.done = True
            eng.halt("found typo")


def is_nonword(obj, eng):
    """
    Quick initial check to see if it is a nonword.
    """
    show_word(obj.interaction, obj.word, obj.details)
    if obj.interaction.get_confirmation("Is non-word?"):
        handle_nonword(obj.word, obj.target, obj.nonword_delegate)
        eng.halt("found nonword")


def is_typo(obj, eng):
    """
    Quick initial check to see if it is a typo.
    """
    show_word(obj.interaction, obj.word, obj.details)
    if obj.interaction.get_confirmation("Is it typo?"):
        handle_typo(obj.interaction, obj.word, obj.details, obj.repopath)
        obj.done = True
        eng.halt("found typo")


def what_now(obj, eng):
    """
    Check to see what else to do.
    """
    show_word(obj.interaction, obj.word, obj.details)
    obj.interaction.send("Todo what now options?")
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
        with open(filename, "rb") as fobj:
            show_next = False
            prev_line = None
            shown = 0
            max_shown = 3
            for linedata in fobj:
                line = linedata.decode("utf-8", "replace").rstrip("\r\n")
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
    joiner = ""
    regexstr = f"(?:^|[^a-zA-Z])({re.escape(word)})(?:$|[^a-zA-Z])"
    if isinstance(line, bytes):
        regexstr = regexstr.encode("utf-8")
        joiner = b""
        replacement = replacement.encode("utf-8")
    regex = re.compile(regexstr, re.I)
    if not regex.search(line):
        return None
    result = []
    pos = 0
    for match in regex.finditer(line):
        match_start = match.start(1)
        match_end = match.end(1)
        result.append(line[pos:match_start])
        match_start_inc = match_start + 1
        if line[match_start:match_start_inc].isupper():
            result.append(replacement.capitalize())
        else:
            result.append(replacement)
        pos = match_end
    result.append(line[pos:])
    return joiner.join(result)


def handle_nonword(word, target, nonword_delegate):  # pylint: disable=unused-argument
    """
    Handle a nonword
    """
    add_non_word(word, target)
    if check_nonwords(target):
        nonword_delegate()
    return False


def handle_typo(
    interaction, word, details, repopath
):  # pylint: disable=unused-argument
    """
    Handle a typo
    """
    newspell = interaction.get_input(f"How do you spell {word}?")
    if newspell:
        fix_word(interaction, word, details, newspell, repopath)
        return True
    return False


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
        if not fix_word_in_file(filename, word, newspell):
            continue
        git = local["git"]
        filepath = Path(filename)
        relpath = str(filepath.relative_to(repopath))
        # plumbum bug workaround
        os.chdir(pathlib.Path.home())
        try:
            with local.cwd(str(repopath)):
                _ = git["add"][relpath] & FG
        except ProcessExecutionError:
            logging.exception("Failed to update %s", relpath)
        else:
            file_paths.append(relpath)
    if file_paths:
        interaction.add_repo_save(repopath, newspell, word, file_paths)
    return True


def fix_word_in_file(filename, word, newspell):
    """
    Perform one file correction
    """
    if word == newspell:
        return False
    lines = []
    fixed = False
    with open(filename, "rb") as fobj:
        for line in fobj:
            output = perform_replacement(line, word, newspell)
            if output is not None:
                lines.append(output)
                fixed = True
            else:
                lines.append(line)
    with open(filename, "wb") as fobj:
        for line in lines:
            fobj.write(line)
    return fixed


def add_repo_save(repodir, add_word, del_word, file_paths):
    """
    Record a typo correction
    """
    reponame = Path(repodir).name
    saves = get_multi_repo(reponame)
    saves.append(
        {
            "reponame": reponame,
            "add_word": add_word,
            "del_word": del_word,
            "file_paths": file_paths,
            "repodir": repodir,
        }
    )
    set_multi_repo(reponame, saves)
