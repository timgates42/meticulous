"""
Add non-words to the unanimous repository
"""

import io
import os
import pathlib
import random
import re
import sys
from pathlib import Path

from plumbum import local

from meticulous._github import check_forked, checkout, create_pr, fork


class RecentNonWord:  # pylint: disable=too-few-public-methods
    """
    Keep any nonwords found recently
    """

    cache = set()


def get_unanimous(target):
    """
    Ensure the local unanimous is loaded and return the path
    """
    orgrepo = "resplendent-dev/unanimous"
    repo = orgrepo.split("/")[-1]
    if not check_forked(orgrepo):
        fork(orgrepo)
    checkoutpath = target / repo
    if not checkoutpath.is_dir():
        checkout(repo, target)
    nonwordpath = checkoutpath / "nonwords.txt"
    return nonwordpath


def add_non_word(word, target):
    """
    Ensure the repository unanimous is checked out and then append to the list
    of non words.
    """
    nonwordpath = get_unanimous(target)
    with io.open(nonwordpath, "a", encoding="utf-8") as fobj:
        print(word, file=fobj)
        RecentNonWord.cache.add(word)


def load_recent_non_words(target):
    """
    Load the Non-Word Cache
    """
    nonwordpath = get_unanimous(target)
    with io.open(nonwordpath, "r", encoding="utf-8") as fobj:
        for line in fobj:
            word = line.strip().lower()
            RecentNonWord.cache.add(word)


def check_nonwords(target):
    """
    Work out if enough nonwords have been collected to be worth submitting
    upstream.
    """
    return get_nonword_count(target) > 5


def update_nonwords(target):
    """
    Commit the current words, pull upstream updates, prepare the unanimous data
    and commit again. Then submit a PR.
    """
    path = get_unanimous(target)
    git = local["git"]
    pyexe = local[sys.executable]
    # plumbum bug workaround
    os.chdir(pathlib.Path.home())
    with local.cwd(str(path.parent)):
        git("add", path.name)
        git("commit", "-m", "update nonwords")
        git("pull", "--no-edit")
    # plumbum bug workaround
    os.chdir(pathlib.Path.home())
    with local.cwd(str(path.parent / "app")):
        pyexe("-m", "unanimous")
    num = random.randrange(100000, 999999)  # noqa: S311,DUO102 # nosec
    to_branch = "master"
    from_branch = f"nonwords_{num}"
    # plumbum bug workaround
    os.chdir(pathlib.Path.home())
    with local.cwd(str(path.parent)):
        git("add", ".")
        git("commit", "-m", "update nonwords")
        git("push", "origin", f"{to_branch}:{from_branch}")
    reponame = "unanimous"
    title = "Add nonwords"
    body = title
    pullreq = create_pr(reponame, title, body, from_branch, to_branch)
    return pullreq


def get_nonword_count(target):
    """
    Run git diff and check lines added
    """
    regex = re.compile("[+][^+]")
    path = get_unanimous(target)
    git = local["git"]
    # plumbum bug workaround
    os.chdir(pathlib.Path.home())
    with local.cwd(str(path.parent)):
        output = git("diff", path.name)
    return len([line for line in output.splitlines() if regex.match(line)])


def is_local_non_word(word):
    """
    Check the local non word cache
    """
    return word.lower() in RecentNonWord.cache


def main():
    """
    Testing entry point
    """
    if check_nonwords(Path(os.environ["HOME"]) / "data"):
        pullreq = update_nonwords(Path(os.environ["HOME"]) / "data")
        print(f"Created PR #{pullreq.number} view at" f" {pullreq.html_url}")


if __name__ == "__main__":
    main()
