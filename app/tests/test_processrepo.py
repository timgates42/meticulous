"""
Test calls for processing github repositories
"""

import os
import shutil
import tempfile

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


@mark.parametrize("source,word,replacement,expected", [
    (b"thier\r\n", "thier", "their", b"their\r\n"),
    (b"thier\n", "thier", "their", b"their\n"),
])
def test_fix_word_in_file(source, word, replacement, expected):
    """
    Ensure word replacement file handling works
    """
    # Setup
    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, "file")
    with open(filename, "wb") as fobj:
        fobj.write(source)
    # Exercise
    _processrepo.fix_word_in_file(filename, word, replacement)
    # Verify
    with open(filename, "rb") as fobj:
        result = fobj.read()
    assert result == expected  # noqa # nosec
    shutil.rmtree(tmpdir)
