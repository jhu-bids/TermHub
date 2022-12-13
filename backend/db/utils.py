"""Utils for database usage"""
import json
from sqlalchemy import create_engine, event
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Dict, Union, List

from backend.db.config import BRAND_NEW_DB_URL, DB_URL, CONFIG, get_pg_connect_url

DEBUG = True
DB = CONFIG["db"]
SCHEMA = CONFIG["schema"]


def get_db_connection(new_db=False, isolation_level='AUTOCOMMIT'):
    """Connect to db"""
    engine = create_engine(get_pg_connect_url(), isolation_level=isolation_level)

    @event.listens_for(engine, "connect", insert=True)
    def set_search_path(dbapi_connection, connection_record):
        # from https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#setting-alternate-search-paths-on-connect
        # HURRAY! finally figured out how to set search path, so don't need to
        #           qualify table names with schema!
        existing_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET SESSION search_path='{SCHEMA}'")
        cursor.close()
        dbapi_connection.autocommit = existing_autocommit

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
    x = show_tables
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


def show_tables(con):
    query = """
        SELECT n.nspname as "Schema", c.relname as "Name",
              CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' WHEN 'i' THEN 'index' WHEN 'S' THEN 'sequence' WHEN 's' THEN 'special' WHEN 't' THEN 'TOAST table' WHEN 'f' THEN 'foreign table' WHEN 'p' THEN 'partitioned table' WHEN 'I' THEN 'partitioned index' END as "Type",
              pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
        FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             LEFT JOIN pg_catalog.pg_am am ON am.oid = c.relam
        WHERE c.relkind IN ('r','p','v','m','S','f','')
          AND n.nspname <> 'pg_catalog'
          AND n.nspname !~ '^pg_toast'
          AND n.nspname <> 'information_schema'
          AND pg_catalog.pg_table_is_visible(c.oid)
        ORDER BY 1,2;
    """
    res = sql_query(con, query)
    return res