"""
Add non-words to the unanimous repository
"""

import io

from meticulous._github import check_forked, checkout, fork


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


def is_local_non_word(word):
    """
    Check the local non word cache
    """
    return word.lower() in RecentNonWord.cache
