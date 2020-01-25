"""
Test process calls
"""

import pathlib
import tempfile

import dataset

from meticulous import _process


def test_get_spelling_store_path():
    """
    Ensure appropriate db path is obtained
    """
    # Setup
    target = pathlib.Path(tempfile.mkdtemp())
    # Exercise
    path = _process.get_spelling_store_path(target)
    # Verify
    dataset.connect(f"sqlite://{path}")
