"""
Main processing for meticulous
"""
from __future__ import absolute_import, division, print_function

import io
import os
import sys
from pathlib import Path

from plumbum import FG, local

from meticulous._github import check_forked, checkout, fork, is_archived
from meticulous._sources import obtain_sources
from meticulous._storage import prepare
from spelling.check import check


def run_invocation(target):
    """
    Execute the invocation
    """
    prepare()
    if target is None:
        target = Path(os.environ["HOME"]) / "data"
    else:
        target = Path(target)
    if not target.is_dir():
        print(f"Target {target} is not a directory.", file=sys.stderr)
        sys.exit(1)
    editor = local["/usr/bin/vim"]
    for orgrepo in obtain_sources():
        _, repo = orgrepo.split("/", 1)
        print(f"Checking {orgrepo}")
        if not check_forked(repo):
            print(f"Have not forked {orgrepo}")
            print(f"Forking {orgrepo}")
            fork(orgrepo)
            if is_archived(orgrepo):
                print(f"Skipping archived repo {orgrepo}")
                continue
            print(f"Checkout {repo}")
            checkout(repo, target)
            repodir = target / repo
            print(f"Running spell check on {repodir}")
            spellpath = repodir / "spelling.txt"
            print(f"Spelling output {spellpath}")
            with io.open(spellpath, "w", encoding="utf-8") as fobj:
                os.chdir(repodir)
                check(True, True, None, fobj)
            print("Opening editor")
            _ = editor["spelling.txt"] & FG
            sys.exit(0)
