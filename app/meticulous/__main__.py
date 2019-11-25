"""
Module load handler for execution via:

python -m meticulous
"""
from __future__ import absolute_import, division, print_function

import re

import click
import urllib3

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

__version__ = "0.1"

SOURCE_MARKDOWN_URLS = [
    "https://raw.githubusercontent.com/vinta/awesome-python/master/README.md"
]


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctxt):
    """
    Main click group handler
    """
    if ctxt.invoked_subcommand is None:
        run_invocation()


@main.command()
def invoke():
    """
    Primary command handler
    """
    run_invocation()


def run_invocation():
    """
    Execute the invocation
    """
    for url in SOURCE_MARKDOWN_URLS:
        check_url(url)


def check_url(url):
    """
    Download and process the
    """
    for link in get_all_markdown_github_links(url):
        print(link)


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
    http = urllib3.PoolManager()
    resp = http.request("GET", url)
    return resp.data.decode("utf-8")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
