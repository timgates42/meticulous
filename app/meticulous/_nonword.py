"""
Add non-words to the unanimous repository
"""

import io

from meticulous._github import check_forked, checkout, fork


def add_non_word(word, target):
    """
    Ensure the repository unanimous is checked out and then append to the list
    of non words.
    """
    orgrepo = "resplendent-dev/unanimous"
    repo = orgrepo.split("/")[-1]
    if not check_forked(orgrepo):
        fork(orgrepo)
    checkoutpath = target / repo
    if not checkoutpath.is_dir():
        checkout(repo, target)
    nonwordpath = checkoutpath / "nonwords.txt"
    with io.open(nonwordpath, "a", encoding="utf-8") as fobj:
        print(word, file=fobj)
