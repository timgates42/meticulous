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


def main(target, start):
    """
    Alternative way of running meticulous in a browser
    """
    host = "0.0.0.0"  # nosec=B104
    port = 3080
    if not start:
        host = get_input("Listen Address: ", host)
        port = int(get_input("Listen Port: ", str(port)))
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
