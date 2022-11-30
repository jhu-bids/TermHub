"""Utils for database usage"""
import json
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Dict, Union

from backend.db.config import BRAND_NEW_DB_URL, DB_URL


def get_db_connection(new_db=False):
    """Connect to db"""
    url = BRAND_NEW_DB_URL if new_db else DB_URL
    engine = create_engine(url)
    return engine.connect()


def database_exists(con: Connection, db_name: str) -> bool:
    """Check if database exists"""
    result = \
        run_sql(con, f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{db_name}';").fetchall()
    return len(result) == 1


def sql_query(
    con: Connection,
    query: Union[text, str],
    params: Dict = {}):
    """Run a sql query with optional params, fetching records.
    https://stackoverflow.com/a/39414254/1368860:
    query = "SELECT * FROM my_table t WHERE t.id = ANY(:ids);"
    conn.execute(sqlalchemy.text(query), ids=some_ids)
    """
    try:
        query = text(query) if not isinstance(query, TextClause) else query
        q = con.execute(query, **params) if params else con.execute(query)
        return q.fetchall()
    except (ProgrammingError, OperationalError):
        raise RuntimeError(f'Got an error executing the following statement:\n{query}, {json.dumps(params, indent=2)}')


def run_sql(con: Connection, command: str):
    """Run a sql command"""
    statement = text(command)
    try:
        return con.execute(statement)
    except (ProgrammingError, OperationalError):
        raise RuntimeError(f'Got an error executing the following statement:\n{command}')
