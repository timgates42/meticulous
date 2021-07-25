"""
Obtain spelling fixes from https://pypi.org/project/codespell/
"""

import os

import codespell_lib._codespell

MISSPELLINGS = {}


class Suggestion:
    """
    Keep details of a suggestion
    """

    def __init__(self, is_nonword=False, is_typo=False, replacement_list=None):
        if replacement_list is None:
            replacement_list = []
        replacement = replacement_list[0] if replacement_list else ""
        self.is_nonword = is_nonword
        self.is_typo = is_typo
        self.replacement = replacement
        self.replacement_list = replacement_list
        self.priority = (
            3
            if self.replacement
            else (2 if self.is_typo else (1 if self.is_nonword else 0))
        )

    def __eq__(self, other):
        """
        Check equality
        """
        return (
            self.is_nonword == getattr(other, "is_nonword", None)
            and self.is_typo == getattr(other, "is_typo", None)
            and self.replacement_list == getattr(other, "replacement_list", None)
        )

    def save(self):
        """
        Save to json dict
        """
        return {
            "is_nonword": self.is_nonword,
            "is_typo": self.is_typo,
            "replacement_list": self.replacement_list,
        }

    @classmethod
    def load(cls, data):
        """
        Load from json dict
        """
        replacement_list = data.get("replacement_list", [])
        replacement = data.get("replacement", [])
        if replacement and not replacement_list:
            replacement_list = [replacement]
        return cls(
            is_nonword=bool(data.get("is_nonword")),
            is_typo=bool(data.get("is_typo")),
            replacement_list=replacement_list,
        )


def load():
    """
    Load in dictionary lists
    """
    dictionaries = [
        "dictionary.txt",
        "dictionary_code.txt",
        "dictionary_names.txt",
        "dictionary_rare.txt",
    ]
    for name in dictionaries:
        # pylint: disable=protected-access
        codespell_lib._codespell.build_dict(
            os.path.join(codespell_lib._codespell._data_root, name),
            MISSPELLINGS,
            set(),
        )


def get_suggestion(word):
    """
    Check a word and provide suggestions
    """
    if not MISSPELLINGS:
        load()
    try:
        misspelling = MISSPELLINGS[word]
    except KeyError:
        return None
    else:
        words = [item.strip() for item in misspelling.data.split(",") if item.strip()]
        if not words:
            return None
        return Suggestion(is_typo=True, replacement_list=words)
