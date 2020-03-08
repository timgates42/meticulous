"""
Environment based console application handlers
"""


import os
import shutil


def get_editor():
    """
    Allow specifying a different editor via the common environment variable
    EDITOR or METICULOUS_EDITOR
    """
    return get_app("EDITOR", "vim")


def get_browser():
    """
    Allow specifying a different browser via the common environment variable
    BROWSER OR METICULOUS_BROWSER
    """
    return get_app("BROWSER", "links")


def get_app(envname, defltval):
    """
    Allow specifying a different command via its common environment variable
    """
    app_cmd = os.environ.get(f"METICULOUS_{envname}", os.environ.get(envname, defltval))
    app_path = shutil.which(app_cmd)
    if app_path is None:
        raise Exception(
            f"{envname} not found, refer to instructions at"
            f" https://meticulous.readthedocs.io/en/latest/"
        )
    return app_path
