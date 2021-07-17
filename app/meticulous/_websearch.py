"""
Use the internet to determine if the provided word is a nonword or a typo
"""

import datetime
import logging
import random
import re
import threading
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

from meticulous._storage import get_json_value, set_json_value
from meticulous._suggestion import Suggestion, get_suggestion as codespell

DICTIONARIES = [
    "https://www.merriam-webster.com/dictionary/",
    "https://en.wikipedia.org/wiki/",
    "https://www.dictionary.com/browse/",
    "https://en.wiktionary.org/wiki/",
    "https://www.collinsdictionary.com/dictionary/english/",
    "https://www.teachingenglish.org.uk/article/",
    "https://www.vocabulary.com/dictionary/",
    "https://www.thefreedictionary.com/",
    "https://www.thesaurus.com/browse/",
    "https://www.yourdictionary.com/",
]
MISSPELLINGS = [
    "https://www.spellchecker.net/misspellings/",
    "https://www.spellcheck.net/misspelled-words/",
]


class GoogleLock:
    """
    Record google query times and avoid flooding google
    """

    def __init__(self):
        self.lock = threading.Condition()
        self.update = datetime.datetime.now()

    @staticmethod
    def get_google_delay():
        """
        Randomized delay
        """
        return datetime.timedelta(seconds=2 + (random.SystemRandom().random() * 3))

    def avoid_google_wrath(self):
        """
        Google is nonplussed about being flooded by queries so ensure we do not
        query excessively frequently
        """
        with self.lock:
            now = datetime.datetime.now()
            delay = (self.update + self.get_google_delay() - now).total_seconds()
            if delay > 0:
                self.lock.wait(delay)
            self.update = datetime.datetime.now()


def get_suggestion(word):
    """
    Use the internet to determine if the provided word is a nonword or a typo
    if a suggestion is not found in codespell
    """
    suggestion = codespell(word)
    if suggestion is not None:
        return suggestion
    key = f"suggestion.{word}"
    existing = get_json_value(key)
    if existing is not None:
        if existing.get("no_suggestion"):
            return None
        return Suggestion.load(existing)
    suggestion = search_suggestion(word)
    if suggestion is None:
        set_json_value(key, {"no_suggestion": True})
        return None
    set_json_value(key, suggestion.save())
    return suggestion


def search_suggestion(word):
    """
    Use the internet to determine if the provided word is a nonword or a typo
    """
    GOOGLE_LOCK.avoid_google_wrath()
    search = f"https://www.google.com.au/search?q={quote(word)}"
    soup = BeautifulSoup(requests.get(search).text, features="lxml")
    for div in soup.find_all("div"):
        text = div.get_text()
        result = get_suggestion_for_divtext(word, text)
        if result is not None:
            return result
    urls = []
    for link in soup.find_all("a"):
        href = link.attrs.get("href")
        if not href:
            continue
        logging.info("Examining url href: %s", href)
        mobj = re.match("[/]url[?]q=([^&#]+)[&#]", href)
        if not mobj:
            continue
        urls.append(unquote(mobj.group(1)).lower())
    for url in urls:
        for dicturl in MISSPELLINGS:
            if url == f"{dicturl}{word}":
                return Suggestion(is_typo=True)
    for url in urls:
        for dicturl in DICTIONARIES:
            if url == f"{dicturl}{word}":
                return Suggestion(is_nonword=True)
    return None


def get_suggestion_for_divtext(word, text):
    """
    Consider the provided text from a div in a search result
    look for a spelling suggestion.
    """
    logging.info("Examining div text: %s", text)
    mobj = re.match("Showing results for ([^(]+)[(]", text)
    if mobj:
        return check_replacement(word, mobj.group(1))
    mobj = re.match("Did you mean: (.*)$", text)
    if mobj:
        return check_replacement(word, mobj.group(1))
    mobj = re.match(
        f"Showing results for (.*)Search instead for" f" {re.escape(word)}", text
    )
    if mobj:
        return check_replacement(word, mobj.group(1))
    return None


def check_replacement(word, replacement):
    """
    Check a suggested replacement and see if it is just a space insertion in
    which case we count as a nonword.
    """
    if replacement.replace(" ", "") == word:
        return Suggestion(is_nonword=True)
    return Suggestion(is_typo=True, replacement_list=[replacement])


GOOGLE_LOCK = GoogleLock()

if __name__ == "__main__":
    print(get_suggestion("altnernatives"))
