"""
Use the internet to determine if the provided word is a nonword or a typo
"""

import re
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup


class Suggestion:
    def __init__(self, is_nonword=False, is_typo=False, replacement=""):
        self.is_nonword = is_nonword
        self.is_typo = is_typo
        self.replacement = replacement

    def __eq__(self, other):
        """
        Check equality
        """
        return (
            self.is_nonword == getattr(other, "is_nonword", None)
            and self.is_typo == getattr(other, "is_typo", None)
            and self.replacement == getattr(other, "replacement", None)
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


def get_suggestion(word):
    """
    Use the internet to determine if the provided word is a nonword or a typo
    """
    search = f"https://www.google.com.au/search?q={quote(word)}"
    search_re = re.compile("[/]url[?]q=([^&#]+)[&#]")
    page = requests.get(search).text
    soup = BeautifulSoup(page, features="lxml")
    for link in soup.find_all("a"):
        href = link.attrs.get("href")
        if not href:
            continue
        mobj = search_re.match(href)
        if not mobj:
            continue
        urlq = mobj.group(1)
        url = unquote(urlq).lower()
        for dicturl in DICTIONARIES:
            if url == f"{dicturl}{word}":
                return Suggestion(is_nonword=True)
    return None


if __name__ == "__main__":
    print(get_suggestion("catenate"))
