"""
Alternative way of running meticulous in a browser
"""

import flask

from meticulous._webstate import STATE

APP = flask.Flask("meticulous")


@APP.route("/")
def index():
    """
    Default route
    """
    return STATE.response()


def main(target):  # pylint: disable=unused-argument
    """
    Alternative way of running meticulous in a browser
    """
    STATE.start()
    try:
        APP.run(host="0.0.0.0", port=3080)
    finally:
        STATE.stop()
