"""
Used to display summary details of repositories
"""

import io
import pathlib
import re
import sys

from colorama import Fore, Style, init


def display_summary(path):
    """
    Include a header and the summary content
    """
    print("=" * 80)
    print(f"{Fore.YELLOW}{path.name}{Style.RESET_ALL}:")
    print("=" * 80)
    display_summary_content(path)
    print("-" * 80)


def display_summary_content(path):
    """
    Display the first 15 interesting lines of a file. To be interesting it must
    start with an alphanumeric letter after whitespace
    """
    count = 0
    regex = re.compile("\\s*[A-Za-z0-9]")
    with io.open(path, "r", encoding="utf-8") as fobj:
        for line in fobj:
            if regex.match(line):
                print(line.rstrip("\r\n"))
                count += 1
                if count == 15:
                    return


def display_repo_intro(path):
    """
    Display READMEs from a repo
    """
    for fpath in path.iterdir():
        if fpath.name.lower().startswith("readme") and fpath.is_file():
            display_summary(fpath)


if __name__ == "__main__":
    init()
    display_repo_intro(pathlib.Path(sys.argv[1]))
