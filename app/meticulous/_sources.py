"""
Obtain a list of repositories to check
"""
from __future__ import absolute_import, division, print_function

import io
import os
import re

import urllib3

from meticulous._storage import get_value, set_value

SOURCE_MARKDOWN_URLS = [
    "https://raw.githubusercontent.com/vinta/awesome-python/master/README.md"
]


def obtain_sources():
    """
    Scan source list and return organizations/repositories
    """
    for url in SOURCE_MARKDOWN_URLS:
        yield from check_url(url)


def check_url(url):
    """
    Download and process the
    """
    key = "github_links|{url}"
    results = get_value(key)
    if results is None:
        results = "\n".join(get_all_markdown_github_links(url))
        set_value(key, results)
    return results.splitlines()


def get_all_markdown_github_links(url):
    """
    Obtain and filter markdown links to repositories.
    """
    links = get_all_markdown_links(url)
    for link in links:
        mobj = re.match(
            "https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/|$)", link
        )
        if mobj:
            yield mobj.group(1)


def get_all_markdown_links(url):
    """
    Obtain all the markdown links in the URL
    """
    data = download_url(url)
    matches = re.findall("[(]([^)]+)[)]", data)
    return matches


def download_url(url):
    """
    Obtain the URL content
    """
    if os.path.isfile("README.md.txt"):
        with io.open("README.md.txt", "r", encoding="utf-8") as fobj:
            return fobj.read()
    http = urllib3.PoolManager()
    resp = http.request("GET", url)
    return resp.data.decode("utf-8")


if __name__ == "__main__":
    print(list(obtain_sources()))
