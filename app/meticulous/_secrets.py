"""
Load GitHub API token for GNU pass secret manager
"""

import subprocess  # noqa=S404 # nosec


def load_api_key():
    """
    Used to load the GitHub API Token
    """
    output = subprocess.check_output(  # noqa=S603 # nosec
        ["/usr/bin/pass", "show", "github-api-token"]
    )
    return output.decode("ascii").strip()


if __name__ == "__main__":
    print(load_api_key())
