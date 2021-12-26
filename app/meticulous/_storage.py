"""
Record current progress to avoid reprocessing
"""

import json
import pathlib
import sqlite3
import threading

import psycopg2

from meticulous._constants import MULTI_SAVE_KEY


def prepare():
    """
    Ensure current db is ready for use
    """
    con = get_db()
    if not check_table_exists(con, "config"):
        with con.cursor() as cur:
            sql = "CREATE TABLE config ( key text, value text )"
            cur.execute(sql)
            con.commit()


def get_value(key, deflt=None):
    """
    Retrieve a stored key value or return a default
    """
    con = get_db()
    with con.cursor() as cur:
        sql = "SELECT value FROM config WHERE key = %s"
        cur.execute(sql, (key,))
        for (value,) in cur:
            return value
        return deflt


def set_value(key, value):
    """
    Remove any old key values and insert a new key/value
    """
    con = get_db()
    with con.cursor() as cur:
        sql = "DELETE FROM config WHERE key = %s"
        cur.execute(sql, (key,))
        sql = "INSERT INTO config ( key, value ) VALUES (%s, %s)"
        cur.execute(sql, (key, value))
    con.commit()


def get_json_value(key, deflt=None):
    """
    Load a Json value for the specified key
    """
    deflt = json.dumps(deflt)
    jsonval = get_value(key, deflt=deflt)
    if jsonval is None:
        return None
    return json.loads(jsonval)


def set_json_value(key, value):
    """
    Serialize and save a Json value
    """
    set_value(key, json.dumps(value))


def check_table_exists(con, table_name):
    """
    Look in the database to see if table exists
    """
    if hasattr(con, "info"):
        # postgres
        sql = (
            "SELECT t.table_name FROM information_schema.tables t"
            " WHERE t.table_schema='public' AND t.table_name=%s"
        )
    else:
        # sqlite
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
    with con.cursor() as cur:
        cur.execute(sql, (table_name,))
        for _ in cur:
            return True
        return False


def get_db():
    """
    Connect to the database
    """
    try:
        return psycopg2.connect(dbname="meticulous")
    except psycopg2.OperationalError:
        pass
    if getattr(threading.local(), "worker", False):
        raise Exception("Workers prevented from DB access")
    dbpath = get_store_dir() / "sqlite.db"
    return sqlite3.connect(str(dbpath))


def get_store_dir():
    """
    Locate the storage directory of this project
    """
    apppath = pathlib.Path.home() / ".meticulous"
    if not apppath.is_dir():
        apppath.mkdir()
    return apppath


def get_multi_repo(reponame):
    """
    Load multiple repository updates
    """
    return [
        item
        for item in get_json_value(MULTI_SAVE_KEY, [])
        if item["reponame"] == reponame
    ]


def set_multi_repo(reponame, value):
    """
    Save multiple repository updates
    """
    save = value + [
        item
        for item in get_json_value(MULTI_SAVE_KEY, [])
        if item["reponame"] != reponame
    ]
    set_json_value(MULTI_SAVE_KEY, save)


if __name__ == "__main__":
    prepare()
