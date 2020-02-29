.. meticulous documentation master file, created by
   sphinx-quickstart on Tue Jul 23 07:42:50 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for meticulous!
================================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Installation
------------

You can install meticulous for `Python`_ via `pip`_ from `PyPI`_.

.. code-block:: bash

    pip install meticulous

Before you begin
----------------

Before you begin make sure your favourite editor is set in your EDITOR
environment variable, alternatively if you want to use a different editor for
meticulous than your default editor you can set this in METICULOUS_EDITOR.

Meticulous will clone repositories that it is fixing to the directory ~/data by
default, however this can be adjusted on the command line to an alternative
location by specifying the --target argument.

The process needs a personal access token to access GitHub and the personal
access token is kept safe using `pass`_ which will need to be installed.

You can find instructions on creating a GitHub personal access token at
`creating a personal access token`_.

It should be added to pass under the entry `github-api-token`.

Quick Start
-----------

After installing meticulous and following the before you begin guide, you can
run it via...

.. code-block:: bash

    python -m meticulous
 
Now you will view the main command line menu. The general
process for finding and fixing typos is...

'add a new repository' which forks and clones a repository and runs the spell
checker to look for typos.

'examine a repository' which opens the spell checker output report in your
chosen editor. You should find a typo to fix and then correct this in the file
it indicates it was found in and then used 'git add' to stage this change.

'prepare a change' examines your staged change to work out what the typo was and
what the correction is.

'prepare a pr/issue' this allows you to examine the contribution guide and issue
templates for a repository to work out if a full or short issue should be
lodged. After an issue is lodged, a commit can be submitted which will create a
pull request that automatically resolves the created issue with the fix to the
typo.

'remove a repository' this cleans up the on-disk clone and the cycle repeats.

.. _`creating a personal access token`: https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line
.. _`pass`: https://www.passwordstore.org/
.. _`Python`: https://www.python.org/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/..

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
