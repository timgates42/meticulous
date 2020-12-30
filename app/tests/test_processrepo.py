"""
Test processrepo calls
"""

from pytest import mark

from meticulous import _processrepo


@mark.parametrize("line,word,replacement,expected", [
    ("thier", "thier", "their", "their"),
    ("Thier", "thier", "their", "Their"),
    ("Bothier can see thier cat", "thier", "their", "Bothier can see their cat"),
])
def test_perform_replacement(line, word, replacement, expected):
    """
    Ensure word replacement takes place
    """
    # Setup
    # Exercise
    result = _processrepo.perform_replacement(line, word, replacement)
    # Verify
    assert result == expected  # noqa # nosec
