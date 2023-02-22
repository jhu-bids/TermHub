"""Utils for database usage"""
import json
import os
import re
import dateutil.parser as dp
from datetime import datetime, timezone

import pandas as pd
# noinspection PyUnresolvedReferences
from psycopg2.errors import UndefinedTable
from sqlalchemy import create_engine, event
from sqlalchemy.engine import LegacyRow, Row, RowMapping
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Any, Dict, Union, List

from backend.db.config import CONFIG, DATASETS_PATH, OBJECTS_PATH, get_pg_connect_url
from backend.utils import commify

DEBUG = False
DB = CONFIG["db"]
SCHEMA = CONFIG["schema"]


def get_db_connection(isolation_level='AUTOCOMMIT', schema: str = SCHEMA, local=False):
    """Connect to db
    :param local: If True, connection is on local instead of production database."""
    engine = create_engine(get_pg_connect_url(local), isolation_level=isolation_level)

    @event.listens_for(engine, "connect", insert=True)
    def set_search_path(dbapi_connection, connection_record):
        """This does "set search_path to n3c;" when you connect.
        https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#setting-alternate-search-paths-on-connect
        :param connection_record: Part of the example but we're not using yet.

        Ideally, we'd want to be able to call this whenever we want. But cannot be called outside of context of
        initializing a connection.
        """
        if not schema:
            return
        existing_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET SESSION search_path='{schema}'")
        cursor.close()
        dbapi_connection.autocommit = existing_autocommit

    return engine.connect()


def chunk_list(input_list: List, chunk_size) -> List[List]:
    """Split a list into chunks"""
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]


def current_datetime():
    """Get current datetime"""
    return datetime.now(timezone.utc).isoformat()


def is_up_to_date(last_updated: Union[datetime, str], threshold_hours=24) -> bool:
    """Checks two datetimes and returns True if the first is less than threshold_hours old."""
    if isinstance(last_updated, str):
        last_updated = dp.parse(last_updated)
    hours_since_update = (dp.parse(current_datetime()) - last_updated).total_seconds() / 60 / 60 \
        if last_updated else threshold_hours + 1
    return hours_since_update < threshold_hours


def check_if_updated(key: str, skip_if_updated_within_hours: int = None) -> bool:
    """Check if table is up to date"""
    with get_db_connection(schema='') as con2:
        results = sql_query(con2, f"SELECT value FROM public.manage WHERE key = '{key}';")
    last_updated = results[0][0] if results else None
    return last_updated and is_up_to_date(last_updated, skip_if_updated_within_hours)


def is_table_up_to_date(table_name: str, skip_if_updated_within_hours: int = None) -> bool:
    """Check if table is up to date"""
    last_updated_key = f'last_updated_{table_name}'
    return check_if_updated(last_updated_key, skip_if_updated_within_hours)


def update_db_status_var(key: str, val: str):
    """Update the `manage` table with information for a given variable, e.g. when a table was last updated
    todo: change to 1 line: INSERT OVERWRITE or UPDATE"""
    with get_db_connection(schema='') as con2:
        run_sql(con2, f"DELETE FROM public.manage WHERE key = '{key}';")
        sql_str = f"INSERT INTO public.manage (key, value) VALUES ('{key}', '{val}');"
        run_sql(con2, sql_str)


def database_exists(con: Connection, db_name: str) -> bool:
    """Check if database exists"""
    result = \
        run_sql(con, f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{db_name}';").fetchall()
    return len(result) == 1


def sql_query(
    con: Connection, query: Union[text, str], params: Dict = {}, debug: bool = DEBUG, return_with_keys=False
) -> List[Union[RowMapping, LegacyRow]]:
    """Run a sql query with optional params, fetching records.
    https://stackoverflow.com/a/39414254/1368860:
    query = "SELECT * FROM my_table t WHERE t.id = ANY(:ids);"
    conn.execute(sqlalchemy.text(query), ids=some_ids)
    """
    try:
        if params:
            query = text(query) if not isinstance(query, TextClause) else query
            q = con.execute(query, **params) if params else con.execute(query)
        else:
            q = con.execute(query)

        if debug:
            print(f'{query}\n{json.dumps(params, indent=2)}')
        if return_with_keys:
            results: List[RowMapping] = q.mappings().all()  # key value pairs
        else:
            results: List[Union[LegacyRow, Row]] = q.fetchall()  # Row/LegacyRow tuples, with additional properties
        return results
    except (ProgrammingError, OperationalError) as err:
        raise RuntimeError(f'Got an error [{err}] executing the following statement:\n{query}, {json.dumps(params, indent=2)}')


def sql_in(lst: List, quote_items=False) -> str:
    if quote_items:
        s: str = ', '.join([f"'{x}'" for x in lst]) or 'NULL'
    else:
        s: str = ', '.join([str(x) for x in lst]) or 'NULL'
    return f' IN ({s}) '

def run_sql(con: Connection, command: str, params: Dict = {}) -> Any:
    """Run a sql command"""
    if params:
        command = text(command) if not isinstance(command, TextClause) else command
        q = con.execute(command, **params) if params else con.execute(command)
    else:
        q = con.execute(command)
    return q
    # try:
    #     return con.execute(command)
    # except (ProgrammingError, OperationalError):
    #     raise RuntimeError(f'Got an error executing the following statement:\n{command}')


def sql_query_single_col(*argv) -> List:
    """Run SQL query on single column"""
    results = sql_query(*argv)
    return [r[0] for r in results]


def show_tables(con=get_db_connection(), print_dump=True):
    """Show tables"""
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
    if print_dump:
        import pandas as pd
        print(pd.DataFrame(res))
        # print('\n'.join([', '.join(r) for r in res])) ugly
        # print(pdump(res)) doesn't work
    return res


def load_csv(
    con: Connection, table: str, table_type: str = ['dataset', 'object'][0], replace_rule='replace if diff row count',
    schema: str = SCHEMA
):
    """Load CSV into table
    :param replace_rule: 'replace if diff row count' or 'do not replace'
      First, will replace table (that is, truncate and load records; will fail if table cols have changed, i think
     'do not replace'  will create new table or load table if table exists but is empty

    - Uses: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    """
    # Edge cases
    existing_rows = 0
    try:
        r = con.execute(f'select count(*) from {table}')
        existing_rows = r.one()[0]
    except Exception as err:
        if isinstance(err.orig, UndefinedTable):
            print(f'INFO: {schema}.{table} does not not exist; will create it')
        else:
            raise err

    if replace_rule == 'do not replace' and existing_rows > 0:
        print(f'INFO: {schema}.{table} exists with {commify(existing_rows)} rows; leaving it')
        return

    # Load table
    path = os.path.join(DATASETS_PATH, f'{table}.csv') if table_type == 'dataset' \
        else os.path.join(OBJECTS_PATH, table, 'latest.csv')
    df = pd.read_csv(path)

    if replace_rule == 'replace if diff row count' and existing_rows == len(df):
        print(f'INFO: {schema}.{table} exists with same number of rows {existing_rows}; leaving it')
        return

    print(f'INFO: \nloading {schema}.{table} into {CONFIG["server"]}:{DB}')
    # Clear data if exists
    try:
        con.execute(text(f'TRUNCATE {table}'))
    except ProgrammingError:
        pass

    # Load
    # `schema='termhub_n3c'`: Passed so Joe doesn't get OperationalError('(pymysql.err.OperationalError) (1050,
    #  "Table \'code_sets\' already exists")')
    #  https://stackoverflow.com/questions/69906698/pandas-to-sql-gives-table-already-exists-error-with-if-exists-append
    kwargs = {'if_exists': 'append', 'index': False, 'schema': schema}
    if CONFIG['server'] == 'mysql':   # this was necessary for mysql, probably not for postgres
        try:
            kwargs['schema'] = DB
            df.to_sql(table, con, **kwargs)
        except Exception as err:
            # if data too long error, change column to longtext and try again
            # noinspection PyUnresolvedReferences
            m = re.match("Data too long for column '(.*)'.*", str(err.orig.args))
            if m:
                run_sql(con, f'ALTER TABLE {table} MODIFY {m[1]} LONGTEXT')
                load_csv(con, table)
            else:
                raise err
    else:
        df.to_sql(table, con, **kwargs)

    update_db_status_var(f'last_updated_{table}', str(current_datetime()))
