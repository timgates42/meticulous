"""
Alternative way of running meticulous in a browser
"""

import flask

from meticulous._input import get_input
from meticulous._webstate import STATE

APP = flask.Flask("meticulous")


@APP.route("/", methods=["POST", "GET"])
def index():
    """
    Default route
    """
    return STATE.response()


def main(target):
    """
    Alternative way of running meticulous in a browser
    """
    host = get_input("Listen Address: ", "0.0.0.0")
    port = int(get_input("Listen Port: ", "3080"))
    run_app(target, host, port)


def run_app(target, host, port):
    """
    Alternative way of running meticulous in a browser
    """
    STATE.start(target)
    try:
        APP.run(host=host, port=port)
    finally:
        STATE.stop()
