"""
Obtain a list of repositories to check
"""
from __future__ import absolute_import, division, print_function

import datetime
import re

import requests

from meticulous._storage import get_value, set_value

TIME_FMT = "%Y-%m-%d %H:%M:%S"
CACHE_TIME_DAYS = 7

SOURCE_MARKDOWN_URLS = [
    "https://raw.githubusercontent.com/timgates42/repository_list/main/README.md",
    "https://raw.githubusercontent.com/vinta/awesome-python/master/README.md",
    "https://raw.githubusercontent.com/shahraizali/awesome-django/master/README.md",
    "https://raw.githubusercontent.com/humiaozuzu/awesome-flask/master/README.md",
    "https://raw.githubusercontent.com/uralbash/awesome-pyramid/master/README.md",
    "https://raw.githubusercontent.com/sorrycc/awesome-javascript/master/README.md",
    "https://raw.githubusercontent.com/kozross/awesome-c/master/README.md",
    "https://raw.githubusercontent.com/aleksandar-todorovic/awesome-c/master/README.md",
    "https://raw.githubusercontent.com/uhub/awesome-c/master/README.md",
    "https://raw.githubusercontent.com/mrezak/awesome-python-1/master/README.md",
    "https://raw.githubusercontent.com/sindresorhus/awesome/master/README.md",
    "https://raw.githubusercontent.com/krishnasumanthm/Awesome-Python/master/README.md",
    "https://raw.githubusercontent.com/mahmoud/awesome-python-applications"
    "/master/README.md",
    "https://raw.githubusercontent.com/trananhkma/fucking-awesome-python"
    "/master/README.md",
]

# Organisations or Users who have requested to be excluded from typo fixes
BLACKLISTED_ORGUSERS = {"angvp"}


def obtain_sources():
    """
    Scan source list and return organizations/repositories
    """
    for url in SOURCE_MARKDOWN_URLS:
        for orgrepo in check_url(url):
            orguser = orgrepo.split("/", 1)[0]
            if orguser in BLACKLISTED_ORGUSERS:
                continue
            yield orgrepo


def check_url(url):
    """
    Download and process the
    """
    now = datetime.datetime.now()
    results = None
    dkey = f"github_links_datetxt|{url}"
    key = f"github_links|{url}"
    datetxt = get_value(dkey)
    if datetxt is not None:
        dobj = datetime.datetime.strptime(datetxt, TIME_FMT)
        if dobj + datetime.timedelta(days=CACHE_TIME_DAYS) > now:
            results = get_value(key)
    if results is None:
        results = "\n".join(get_all_markdown_github_links(url))
        set_value(key, results)
        set_value(dkey, now.strftime(TIME_FMT))
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
    return requests.get(url, timeout=120).text


if __name__ == "__main__":
    print(list(obtain_sources()))
