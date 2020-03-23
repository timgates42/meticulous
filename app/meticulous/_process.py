"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import os
import re
import shutil
import sys
from pathlib import Path

import spelling.version
import unanimous.util
import unanimous.version
from colorama import Fore, Style, init
from plumbum import FG, local
from spelling.store import get_store
from workflow.engine import GenericWorkflowEngine

from meticulous._github import create_pr, get_parent_repo
from meticulous._input import (
    UserCancel,
    get_confirmation,
    make_choice,
    make_simple_choice,
)
from meticulous._multiworker import (
    add_repo_save,
    interactive_add_one_new_repo,
    interactive_task_collect_nonwords,
)
from meticulous._multiworker import main as multiworker_main
from meticulous._nonword import load_recent_non_words
from meticulous._storage import get_json_value, prepare, set_json_value
from meticulous._summary import display_and_check_files
from meticulous._util import get_editor


def get_spelling_store_path(target):
    """
    DB to store spelling stats
    """
    path = target / ".meticulous"
    if not path.is_dir():
        path.mkdir()
    return path / "spelling.db"


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
    load_recent_non_words(target)
    validate_versions()
    try:
        if get_confirmation("Run automated process?"):
            automated_process(target)
            while get_confirmation("Run automated process again?"):
                automated_process(target)
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
                "automated work queue": automated_work_queue,
                "examine a repository": examine_repo_selection,
                "manually add a new repository": manually_add_new_repo,
                "remove a repository": remove_repo_selection,
                "add a new repository": add_new_repo,
                "prepare a change": prepare_a_change,
                "prepare a pr/issue": prepare_a_pr_or_issue,
                "show statistics": show_statistics,
            }
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
    remove_repo_for(repo, repodir)


def remove_repo_for(repo, repodir, confirm=True):
    """
    Remove specified repo
    """
    for name in ("repository_map", "repository_saves"):
        repository_map = get_json_value(name, {})
        try:
            del repository_map[repo]
            set_json_value(name, repository_map)
        except KeyError:
            continue
    if confirm:
        option = make_simple_choice(["Yes", "No"], "Delete the directory?")
    else:
        option = "Yes"
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
    prepare_a_pr_or_issue_for(reponame, reposave)


def fast_prepare_a_pr_or_issue_for(reponame, reposave):
    """
    Display a suggestion if the repository looks like it wants an issue and a
    pull request or is happy with just a pull request.
    """
    repopath = Path(reposave["repodir"])
    suggest_issue = False
    if display_and_check_files(repopath / ".github" / "ISSUE_TEMPLATE"):
        suggest_issue = True
    if display_and_check_files(repopath / ".github" / "pull_request_template.md"):
        suggest_issue = True
    if display_and_check_files(repopath / "CONTRIBUTING.md"):
        suggest_issue = True
    if not suggest_issue:
        if get_confirmation("Analysis suggests plain pr, agree?"):
            plain_pr_for(reponame, reposave)
            return
    prepare_a_pr_or_issue_for(reponame, reposave)


def plain_pr_for(reponame, reposave):
    """
    Create and submit the standard PR.
    """
    make_a_commit(reponame, reposave, False)
    submit_commit(reponame, reposave, None)


def prepare_a_pr_or_issue_for(reponame, reposave):
    """
    Access repository to prepare a change
    """
    try:
        while True:
            repodir = reposave["repodir"]
            repodirpath = Path(repodir)
            choices = get_pr_or_issue_choices(reponame, repodirpath)
            option = make_choice(choices)
            if option is None:
                return
            handler, context = option
            handler(reponame, reposave, context)
    except UserCancel:
        print("quit - returning to main process")


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
    choices["make a commit"] = (make_a_commit, False)
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
docs: Fix simple typo, {del_word} -> {add_word}

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
    file_paths = reposave["file_paths"]
    files = ", ".join(file_paths)
    issue_path = str(repodir / "__issue__.txt")
    title, body = load_commit_like_file(issue_path)
    issue_num = issue_via_api(reponame, title, body)
    commit_path = str(repodir / "__commit__.txt")
    with io.open(commit_path, "w", encoding="utf-8") as fobj:
        print(
            f"""\
docs: Fix simple typo, {del_word} -> {add_word}

There is a small typo in {files}.

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
    pullreq = create_pr(reponame, title, body, from_branch, to_branch)
    print(f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}")


def push_commit(repodir, add_word):
    """
    Create commit and push
    """
    git = local["git"]
    with local.cwd(repodir):
        to_branch = git("symbolic-ref", "--short", "HEAD").strip()
        from_branch = f"bugfix_typo_{add_word.replace(' ', '_')}"
        _ = git["commit", "-F", "__commit__.txt"] & FG
        _ = git["push", "origin", f"{to_branch}:{from_branch}"] & FG
    return from_branch, to_branch


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
        add_repo_save(repodir, add_word, del_word, file_paths)


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
    return interactive_add_one_new_repo(target)


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


def automated_work_queue(target):  # pylint: disable=unused-argument
    """
    Run the multi task work queue
    """
    multiworker_main(target)


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
    reponame = next(iter(repository_list.keys()))
    interactive_task_collect_nonwords(reponame, obj.target)


def task_submit(obj, eng):  # pylint: disable=unused-argument
    """
    Submits the typo
    """
    repository_saves = get_json_value("repository_saves", {})
    count = len(repository_saves)
    if count != 1:
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
    if count != 1:
        print(f"Unexpected number of repostories - {count}")
        return
    reponame, reposave = next(iter(repository_map.items()))
    remove_repo_for(reponame, reposave, confirm=False)
