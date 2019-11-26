"""
Load GitHub API token for GNU pass secret manager
"""

import subprocess


def load_api_key():
    """
    Used to load the GitHub API Token
    """
    output = subprocess.check_output(["pass", "show", "github-api-token"])
    return output.decode("ascii").strip()


if __name__ == "__main__":
    print(load_api_key())
