#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
`setuptools` Distribution for meticulous
"""

# System  Imports
import codecs
import os
import re

# External Imports
from setuptools import find_packages, setup

PACKAGE_NAME = "meticulous"
URL = "https://github.com/timgates42/meticulous"
GITHUB_ORG = "timgates42"
GITHUB_REPO = "meticulous"
RE_SUB = "(https://github.com/%s/%s/blob/master/\\g<1>)" % (GITHUB_ORG, GITHUB_REPO)


def load_include(fname, transform=False):
    """
    Read the contents of relative `README` file.
    """
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with codecs.open(file_path, encoding="utf-8") as fobj:
        data = fobj.read()
        if not transform:
            return data
        markdown_fixed = re.sub("[(]([^)]*[.](?:md|rst))[)]", RE_SUB, data)
        rst_fixed = re.sub(
            "^[.][.] [_][`][^`]*[`][:] ([^)]*[.](?:md|rst))", RE_SUB, markdown_fixed
        )
        return rst_fixed


def read_version():
    """
    Read the contents of relative file.
    """
    file_path = os.path.join(os.path.dirname(__file__), PACKAGE_NAME, "version.py")
    regex = re.compile("__version__ = ['\"]([^'\"]*)['\"]")
    with codecs.open(file_path, encoding="utf-8") as fobj:
        for line in fobj:
            mobj = regex.match(line)
            if mobj:
                return mobj.group(1)
    raise Exception("Failed to read version")


setup(
    name=PACKAGE_NAME,
    version=read_version(),
    author="Tim Gates",
    author_email="tim.gates@iress.com",
    maintainer="Tim Gates",
    maintainer_email="tim.gates@iress.com",
    packages=find_packages(exclude=["tests"]),
    license="GPLv3+",
    description=load_include("short_description.txt")
    .replace("\n", " ")
    .replace("\r", "")
    .strip(),
    long_description=load_include("README.md", transform=True),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    test_suite="tests",
    test_requires=[
        elem.strip()
        for elem in load_include("test_requires.txt").splitlines()
        if elem.strip()
    ],
    install_requires=[
        elem.strip()
        for elem in load_include("requirements.txt").splitlines()
        if elem.strip()
    ],
    url=URL,
    classifiers=[
        elem
        for elem in [
            "Development Status :: 4 - Beta",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Operating System :: OS Independent",
            "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        ]
        if elem
    ],
)
