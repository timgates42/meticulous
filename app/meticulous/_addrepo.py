"""
Manage process of adding repositories
"""

import io
import json
import subprocess  # noqa=S404 # nosec
import sys

import unanimous

from meticulous._github import (
    check_forked,
    checkout,
    fork,
    get_true_orgrepo,
    is_archived,
    issues_allowed,
)
from meticulous._nonword import is_local_non_word
from meticulous._sources import obtain_sources
from meticulous._storage import get_json_value, set_json_value
from meticulous._summary import display_repo_intro
from meticulous._websearch import get_suggestion


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
