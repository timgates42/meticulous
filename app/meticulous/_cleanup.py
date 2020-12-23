"""
Upon completion cleanup
"""

import os
import shutil

from meticulous._input import make_simple_choice
from meticulous._storage import get_json_value, set_json_value


def remove_repo_for(repo, repodir, confirm=True):
    """
    Remove specified repo
    """
    for name in ("repository_map", "repository_saves"):
        repository_map = get_json_value(name, {})
        try:
            del repository_map[repo]
            set_json_value(name, repository_map)
        except KeyError:
            continue
    if confirm:
        option = make_simple_choice(["Yes", "No"], "Delete the directory?")
    else:
        option = "Yes"
    if option == "Yes":
        if os.path.isdir(repodir):
            shutil.rmtree(repodir, ignore_errors=True)
