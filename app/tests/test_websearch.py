"""
Test cases for search results
"""

import logging

import pytest

from meticulous._websearch import Suggestion, get_suggestion


@pytest.mark.parametrize(
    "word, expected",
    [
        ("catenate", Suggestion(is_nonword=True)),
        ("actuall", Suggestion(is_typo=True)),
        ("altnernatives", Suggestion(is_typo=True, replacement="alternatives")),
        ("pressent", Suggestion(is_typo=True, replacement="present")),
        ("cssrewrite", Suggestion(is_nonword=True)),
    ],
)
def test_suggestions(caplog, word, expected):
    """
    Test to ensure expected suggestions are obtained
    """
    # Setup
    with caplog.at_level(logging.INFO):
        # Exercise
        obtained = get_suggestion(word)
    # Verify
    assert obtained == expected  # noqa: S101 # nosec
