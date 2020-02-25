"""
Test cases for search results
"""

import pytest

from meticulous._websearch import Suggestion, get_suggestion


@pytest.mark.parametrize(
    "word, expected", [
        ("catenate", Suggestion(is_nonword=True)),
        ("actuall", Suggestion(is_typo=True)),
        ("altnernatives", Suggestion(is_typo=True, replacement="alternatives")),
    ],
)
def test_suggestions(word, expected):
    """
    Test to ensure expected suggestions are obtained
    """
    # Exercise
    obtained = get_suggestion(word)
    # Verify
    assert obtained == expected
