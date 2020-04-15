"""
Use the internet to determine if the provided word is a nonword or a typo
"""

import logging
import re
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup


class Suggestion:
    """
    Keep details of a websearch suggestion
    """

    def __init__(self, is_nonword=False, is_typo=False, replacement=""):
        self.is_nonword = is_nonword
        self.is_typo = is_typo
        self.replacement = replacement
        self.priority = (
            3
            if self.replacement is not None
            else (2 if self.is_typo else (1 if self.is_nonword else 0))
        )

    def __eq__(self, other):
        """
        Check equality
        """
        return (
            self.is_nonword == getattr(other, "is_nonword", None)
            and self.is_typo == getattr(other, "is_typo", None)
            and self.replacement == getattr(other, "replacement", None)
        )

    def save(self):
        """
        Save to json dict
        """
        return {
            "is_nonword": self.is_nonword,
            "is_typo": self.is_typo,
            "replacement": self.replacement,
        }

    @classmethod
    def load(cls, data):
        """
        Load from json dict
        """
        return cls(
            is_nonword=bool(data.get("is_nonword")),
            is_typo=bool(data.get("is_typo")),
            replacement=data.get("replacement", ""),
        )


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


def get_suggestion(word):
    """
    Use the internet to determine if the provided word is a nonword or a typo
    """
    search = f"https://www.google.com.au/search?q={quote(word)}"
    soup = BeautifulSoup(requests.get(search).text, features="lxml")
    for div in soup.find_all("div"):
        text = div.get_text()
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


def check_replacement(word, replacement):
    """
    Check a suggested replacement and see if it is just a space insertion in
    which case we count as a nonword.
    """
    if replacement.replace(" ", "") == word:
        return Suggestion(is_nonword=True)
    return Suggestion(is_typo=True, replacement=replacement)


if __name__ == "__main__":
    print(get_suggestion("altnernatives"))
