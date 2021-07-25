"""
Test cases for search results
"""

import logging

import pytest

from meticulous._websearch import Suggestion, search_suggestion


@pytest.mark.parametrize(
    "word, expected",
    [
        ("catenate", Suggestion(is_nonword=True)),
        ("actuall", Suggestion(is_typo=True)),
        ("altnernatives", Suggestion(is_typo=True, replacement_list=["alternatives"])),
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
        obtained = search_suggestion(word)
    # Verify
    assert obtained.is_nonword == expected.is_nonword  # noqa: S101 # nosec
    assert obtained.is_typo == expected.is_typo  # noqa: S101 # nosec
    assert obtained.replacement == expected.replacement  # noqa: S101 # nosec
