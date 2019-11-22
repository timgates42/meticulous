"""
Configuration file for the Sphinx documentation builder.
"""
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config
#
# pylint: disable=invalid-name,redefined-builtin

# -- Path setup --------------------------------------------------------------

import os
import sys

appdirname = "app"
pyname = "module_goes_here"
sys.path.insert(0, os.path.abspath(os.path.join("..", appdirname)))


# -- Project information -----------------------------------------------------

project = "module_goes_here"
copyright = "2019, name_goes_here"
author = "name_goes_here"


def read_version():
    """
    Read the contents of relative file.
    """
    import re
    import codecs

    file_path = os.path.join("..", appdirname, pyname, "version.py")
    regex = re.compile("__version__ = ['\"]([^'\"]*)['\"]")
    with codecs.open(file_path, encoding="utf-8") as fobj:
        for line in fobj:
            mobj = regex.match(line)
            if mobj:
                return mobj.group(1)
    raise Exception("Failed to read version")


# The full version, including alpha/beta/rc tags
release = read_version()


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.coverage", "sphinx.ext.napoleon"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Sphinx 2.0 changes from index to contents
master_doc = "index"
