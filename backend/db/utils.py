"""Utils for database usage"""
import json
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Dict, Union, List

from backend.db.config import BRAND_NEW_DB_URL, DB_URL

DEBUG = True

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

        if DEBUG:
            print(f'{query}\n{json.dumps(params, indent=2)}')
        return q.fetchall()
    except (ProgrammingError, OperationalError) as err:
        raise RuntimeError(f'Got an error [{err}] executing the following statement:\n{query}, {json.dumps(params, indent=2)}')


def run_sql(con: Connection, command: str):
    """Run a sql command"""
    statement = text(command)
    try:
        return con.execute(statement)
    except (ProgrammingError, OperationalError):
        raise RuntimeError(f'Got an error executing the following statement:\n{command}')

def get_concept_set_members(con,
                            codeset_ids: List[int],
                            columns: Union[List[str], None] = None,
                            column: Union[str, None] = None):
    if column:
        columns = [column]
    if not columns:
        columns = ['codeset_id', 'concept_id']

    # should check that column names are valid columns in concept_set_members
    query = f"""
        SELECT DISTINCT {', '.join(columns)}
        FROM concept_set_members csm
        WHERE csm.codeset_id = ANY(:codeset_ids)
    """
    res = sql_query(con, query, {'codeset_ids': codeset_ids})
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        return [r[0] for r in res]
    return res
