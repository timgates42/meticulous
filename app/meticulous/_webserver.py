"""
Alternative way of running meticulous in a browser
"""

import flask
from meticulous._webstate import STATE

APP = flask.Flask("meticulous")


@APP.route("/", methods=['POST', 'GET'])
def index():
    """
    Default route
    """
    return STATE.response()


def main(target):
    """
    Alternative way of running meticulous in a browser
    """
    STATE.start(target)
    try:
        APP.run(host="0.0.0.0", port=3080)
    finally:
        STATE.stop()
