"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

from colorama import Fore, Style, init
from plumbum import FG, local
from PyInquirer import prompt
from spelling.check import process_results, run_spell_check
from spelling.store import get_store
from workflow.engine import GenericWorkflowEngine
from workflow.errors import HaltProcessing

from meticulous._github import (
    check_forked,
    checkout,
    fork,
    get_api,
    get_parent_repo,
    get_true_orgrepo,
    is_archived,
    issues_allowed,
)
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, prepare, set_json_value


def get_spelling_store_path(target):
    """
    DB to store spelling stats
    """
    path = target / ".meticulous"
    if not path.is_dir():
        path.mkdir()
    return path / "spelling.db"


def make_simple_choice(choices, message="What do you want to do?"):
    """
    Make a choice using a simple {key: key} list of choices
    """
    return make_choice({choice: choice for choice in choices}, message=message)


def make_choice(choices, message="What do you want to do?"):
    """
    Call PyInquirer/prompt-toolkit to make a choice
    """
    choicelist = sorted(list(choices.keys()))
    choicelist.append("- quit -")
    menu = [
        {"type": "list", "name": "option", "message": message, "choices": choicelist}
    ]
    answers = prompt(menu)
    option = answers.get("option", "- quit -")
    return choices.get(option)


def get_confirmation(message="Do you want to continue", defaultval=True):
    """
    Call PyInquirer/prompt-toolkit to make a confirmation
    """
    menu = [
        {"type": "confirm", "message": message, "name": "choice", "default": defaultval}
    ]
    answers = prompt(menu)
    return answers.get("choice")


def get_input(message):
    """
    Call PyInquirer/prompt-toolkit to make a simple input
    """
    menu = [{"type": "input", "name": "option", "message": message}]
    answers = prompt(menu)
    option = answers.get("option")
    return option


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
    init()
    prepare()
    if get_confirmation("Run automated process"):
        automated_process(target)
    else:
        manual_menu(target)


def manual_menu(target):
    """
    Present the main menu
    """
    while True:
        try:
            lookup = {
                "automated process": automated_process,
                "examine a repository": examine_repo_selection,
                "manually add a new repository": manually_add_new_repo,
                "remove a repository": remove_repo_selection,
                "add a new repository": add_new_repo,
                "prepare a change": prepare_a_change,
                "prepare a pr/issue": prepare_a_pr_or_issue,
                "show statistics": show_statistics,
            }
            if not lookup:
                lookup["test"] = test
            handler = make_choice(lookup)
            if handler is None:
                print("Goodbye.")
                return
            handler(target)
        except ProcessingFailed:
            continue


def show_statistics(target):
    """
    Display details about the most common words
    """
    storage_path = get_spelling_store_path(target)
    store = get_store(storage_path)
    word_count = store.load_word_count()
    print(repr(word_count))


def remove_repo_selection(target):  # pylint: disable=unused-argument
    """
    Select an available repository to remove
    """
    os.chdir(target)
    repo, repodir = pick_repo()
    for name in ("repository_map", "repository_saves"):
        repository_map = get_json_value(name, {})
        try:
            del repository_map[repo]
            set_json_value(name, repository_map)
        except KeyError:
            continue
    option = make_simple_choice(["Yes", "No"], "Delete the directory?")
    if option == "Yes":
        shutil.rmtree(repodir)


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
    while True:
        repodir = reposave["repodir"]
        repodirpath = Path(repodir)
        choices = get_pr_or_issue_choices(reponame, repodirpath)
        option = make_choice(choices)
        if option is None:
            return
        handler, context = option
        handler(reponame, reposave, context)


def get_pr_or_issue_choices(reponame, repodirpath):  # pylint: disable=too-many-locals
    """
    Work out the choices menu for pr/issue
    """
    issue_template = Path(".github") / "ISSUE_TEMPLATE"
    pr_template = Path(".github") / "pull_request_template.md"
    contrib_guide = Path("CONTRIBUTING.md")
    issue = Path("__issue__.txt")
    commit = Path("__commit__.txt")
    prpath = Path("__pr__.txt")
    no_issues = Path("__no_issues__.txt")
    choices = {}
    paths = (
        issue_template,
        pr_template,
        contrib_guide,
        prpath,
        issue,
        commit,
        no_issues,
    )
    for path in paths:
        has_path = (repodirpath / path).exists()
        print(f"{reponame} {'HAS' if has_path else 'does not have'}" f" {path}")
        if has_path:
            choices[f"show {path}"] = (show_path, path)
    repo_disables_issues = (repodirpath / no_issues).exists()
    if repo_disables_issues:
        choices["make a commit"] = (make_a_commit, False)
    else:
        choices["make a full issue"] = (make_issue, True)
        choices["make a short issue"] = (make_issue, False)
    has_issue = (repodirpath / issue).exists()
    if has_issue:
        choices["submit issue"] = (submit_issue, None)
    has_commit = (repodirpath / commit).exists()
    if has_commit:
        choices["submit commit"] = (submit_commit, None)
        choices["submit issue"] = (submit_issue, None)
    return choices


def make_issue(reponame, reposave, is_full):  # pylint: disable=unused-argument
    """
    Prepare an issue template file
    """
    add_word = reposave["add_word"]
    del_word = reposave["del_word"]
    file_paths = reposave["file_paths"]
    repodir = Path(reposave["repodir"])
    files = ", ".join(file_paths)
    title = f"Fix simple typo: {del_word} -> {add_word}"
    if is_full:
        body = f"""\
# Issue Type

[x] Bug (Typo)

# Steps to Replicate

1. Examine {files}.
2. Search for `{del_word}`.

# Expected Behaviour

1. Should read `{add_word}`.
"""
    else:
        body = f"""\
There is a small typo in {files}.
Should read `{add_word}` rather than `{del_word}`.
"""
    with io.open(str(repodir / "__issue__.txt"), "w", encoding="utf-8") as fobj:
        print(title, file=fobj)
        print("", file=fobj)
        print(body, file=fobj)


def make_a_commit(reponame, reposave, is_full):  # pylint: disable=unused-argument
    """
    Prepare a commit template file
    """
    add_word = reposave["add_word"]
    del_word = reposave["del_word"]
    file_paths = reposave["file_paths"]
    repodir = Path(reposave["repodir"])
    files = ", ".join(file_paths)
    commit_path = str(repodir / "__commit__.txt")
    with io.open(commit_path, "w", encoding="utf-8") as fobj:
        print(
            f"""\
Fix simple typo: {del_word} -> {add_word}

There is a small typo in {files}.
Should read `{add_word}` rather than `{del_word}`.
""",
            file=fobj,
        )


def submit_issue(reponame, reposave, ctxt):  # pylint: disable=unused-argument
    """
    Push up an issue
    """
    repodir = Path(reposave["repodir"])
    add_word = reposave["add_word"]
    del_word = reposave["del_word"]
    issue_path = str(repodir / "__issue__.txt")
    title, body = load_commit_like_file(issue_path)
    issue_num = issue_via_api(reponame, title, body)
    commit_path = str(repodir / "__commit__.txt")
    with io.open(commit_path, "w", encoding="utf-8") as fobj:
        print(
            f"""\
Fix simple typo: {del_word} -> {add_word}

Closes #{issue_num}
""",
            file=fobj,
        )


def issue_via_api(reponame, title, body):
    """
    Create an issue via the API
    """
    repo = get_parent_repo(reponame)
    issue = repo.create_issue(title=title, body=body)
    return issue.number


def load_commit_like_file(path):
    """
    Read title and body from a well formatted git commit
    """
    with io.open(path, "r", encoding="utf-8") as fobj:
        title = fobj.readline().strip()
        blankline = fobj.readline().strip()
        if blankline != "":
            raise Exception(f"Needs to be a blank second line for {path}.")
        body = fobj.read()
    return title, body


def submit_commit(reponame, reposave, ctxt):  # pylint: disable=unused-argument
    """
    Push up a commit
    """
    repodir = Path(reposave["repodir"])
    add_word = reposave["add_word"]
    commit_path = str(repodir / "__commit__.txt")
    title, body = load_commit_like_file(commit_path)
    from_branch, to_branch = push_commit(repodir, add_word)
    create_pr(reponame, title, body, from_branch, to_branch)


def push_commit(repodir, add_word):
    """
    Create commit and push
    """
    git = local["git"]
    with local.cwd(repodir):
        to_branch = git("symbolic-ref", "--short", "HEAD").strip()
        from_branch = f"bugfix/typo_{add_word}"
        _ = git["commit", "-F", "__commit__.txt"] & FG
        _ = git["push", "origin", f"{to_branch}:{from_branch}"] & FG
    return from_branch, to_branch


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
    print(f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}")


def show_path(reponame, reposave, path):  # pylint: disable=unused-argument
    """
    Display the issue template directory
    """
    print("Opening editor")
    editor = local[get_editor()]
    repodir = reposave["repodir"]
    with local.cwd(repodir):
        _ = editor[str(path)] & FG


def add_change_for_repo(repodir):
    """
    Work out the staged commit and prepare an issue and pull request based on
    the change
    """
    del_word, add_word, file_paths = get_typo(repodir)
    print(f"Changing {del_word} to {add_word} in {', '.join(file_paths)}")
    option = make_simple_choice(["save"], "Do you want to save?")
    if option == "save":
        saves = get_json_value("repository_saves", {})
        reponame = Path(repodir).name
        saves[reponame] = {
            "add_word": add_word,
            "del_word": del_word,
            "file_paths": file_paths,
            "repodir": repodir,
        }
        set_json_value("repository_saves", saves)


def get_typo(repodir):
    """
    Look in the staged commit for the typo.
    """
    git = local["git"]
    del_lines = []
    add_lines = []
    file_paths = []
    with local.cwd(repodir):
        output = git("diff", "--staged")
        for line in output.splitlines():
            if line.startswith("--- a/"):
                index = len("--- a/")
                file_path = line[index:]
                file_paths.append(file_path)
        for line in output.splitlines():
            if line.startswith("-") and not line.startswith("--- "):
                del_lines.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++ "):
                add_lines.append(line[1:])
    if not del_lines or not add_lines:
        print("Could not read diff", file=sys.stderr)
        raise ProcessingFailed()
    del_words = re.findall("[a-zA-Z]+", del_lines[0])
    add_words = re.findall("[a-zA-Z]+", add_lines[0])
    for del_word, add_word in zip(del_words, add_words):
        if del_word != add_word:
            return del_word, add_word, file_paths
    print("Could not locate typo", file=sys.stderr)
    raise ProcessingFailed()


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
        add_one_new_repo(target)


def add_one_new_repo(target):
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
    all_results = list(
        run_spell_check(
            config=None,
            storage_path=get_spelling_store_path(target),
            workingpath=repodir,
        )
    )
    with io.open(spellpath, "w", encoding="utf-8") as fobj:
        success = True
        for line in process_results(all_results, True, True):
            print(line, file=fobj)
            success = False
        if success:
            print("Spelling check passed :)", file=fobj)
    jsonobj = results_to_json(all_results)
    jsonpath = repodir / "spelling.json"
    with io.open(jsonpath, "w", encoding="utf-8") as fobj:
        json.dump(jsonobj, fobj)
    repository_map = get_json_value("repository_map", {})
    repository_map[repo] = str(repodir)
    set_json_value("repository_map", repository_map)
    if not issues_allowed(repo):
        no_issues_path = repodir / "__no_issues__.txt"
        with io.open(no_issues_path, "w", encoding="utf-8") as fobj:
            print("No Issues.", file=fobj)


def results_to_json(all_results):
    """
    Save the result format in a machine processable format.
    """
    words = {}
    for results in all_results:
        if results.words:
            for word in results.words:
                filename = context_to_filename(results.context)
                words.setdefault(word, []).append(
                    {"category": results.category, "file": filename}
                )
    return words


def context_to_filename(name):
    """
    Turn a context line into the filepath.
    """
    testname = name
    if os.path.isfile(testname):
        return testname
    testname = testname.split(":", 1)[0]
    if os.path.isfile(testname):
        return testname
    testname = testname.rsplit("(", 1)[0]
    if os.path.isfile(testname):
        return testname
    raise Exception(f"Unable to get filepath for {name}")


def test(target):  # pylint: disable=unused-argument
    """
    Prompt for a organization and repository to test
    """
    orgrepo = get_input("What organization/repository name?")
    if orgrepo is None:
        return
    print(get_true_orgrepo(orgrepo))


def get_editor():
    """
    Allow specifying a different editor via the common environment variable
    EDITOR or METICULOUS_EDITOR
    """
    editor_cmd = os.environ.get("METICULOUS_EDITOR", os.environ.get("EDITOR", "vim"))
    editor_path = shutil.which(editor_cmd)
    if editor_path is None:
        raise Exception(
            "Editor not found, refer to instructions at"
            " https://meticulous.readthedocs.io/en/latest/"
        )
    return editor_path


def get_browser():
    """
    Allow specifying a different browser via the common environment variable
    BROWSER or METICULOUS_BROWSER
    """
    browser_cmd = os.environ.get(
        "METICULOUS_BROWSER", os.environ.get("BROWSER", "links")
    )
    browser_path = shutil.which(browser_cmd)
    if browser_path is None:
        raise Exception(
            "Browser not found, refer to instructions at"
            " https://meticulous.readthedocs.io/en/latest/"
        )
    return browser_path


def automated_process(target):  # pylint: disable=unused-argument
    """
    Work out the current point in the automated workflow and process the next
    step.
    """
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace([task_add_repo, task_collect_nonwords, task_submit])
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
        add_one_new_repo(obj.target)


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


def task_collect_nonwords(obj, eng):  # pylint: disable=unused-argument
    """
    Saves nonwords until a typo is found
    """
    key = "repository_map"
    repository_list = get_json_value(key, {})
    count = len(repository_list)
    if count != 1:
        print(f"Unexpected number of repostories - {count}")
        return
    repodir = next(iter(repository_list.values()))
    repodirpath = Path(repodir)
    jsonpath = repodirpath / "spelling.json"
    with io.open(jsonpath, "r", encoding="utf-8") as fobj:
        jsonobj = json.load(fobj)
    words = get_sorted_words(jsonobj)
    my_engine = GenericWorkflowEngine()
    my_engine.callbacks.replace([is_nonword, is_typo, what_now])
    for word in words:
        try:
            my_engine.process(
                [NonwordState(target=obj.target, word=word, details=jsonobj[word], repopath=repodirpath)]
            )
        except HaltProcessing:
            return


def is_nonword(obj, eng):
    """
    Quick initial check to see if it is a nonword.
    """
    show_word(obj.word, obj.details)
    if get_confirmation("Is non-word?"):
        handle_nonword(obj.word, obj.details)
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
    files = sorted(set(context_to_filename(detail["file"]) for detail in details))
    for filename in files:
        print(f"{filename}:")
        with io.open(filename, "r", encoding="utf-8") as fobj:
            for line in fobj:
                line = line.rstrip("\r\n")
                output = get_colourized(line, word)
                if output:
                    print(output)


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


def handle_nonword(word, details):  # pylint: disable=unused-argument
    """
    Handle a nonword
    """
    print("Todo handle nonword.")


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
    files = sorted(set(context_to_filename(detail["file"]) for detail in details))
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
        with local.cwd(str(repopath)):
            git['add'][filename]


def get_sorted_words(jsonobj):
    """
    Sort the words first by frequency
    """
    order = []
    for word, details in jsonobj.items():
        order.append(((len(details),), word))
    order.sort()
    return [word for _, word in order]


def task_submit(obj, eng):  # pylint: disable=unused-argument
    """
    Submits the typo
    """
    print(f"Submitting typo...")
