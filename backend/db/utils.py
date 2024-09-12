"""Utils for database usage

todo's
  1. Some functions could be improved using `sql_query()` `params` arg to be less prone to sql injection.
  2. Making 'Connection' optional: Can write a wrapper function and decorate all functions that need, where all it does
  is `conn = con if con else get_db_connection()`, run the inner function, and then close conn if not con.
"""
import json
import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path
from random import randint

import pytz
import dateutil.parser as dp
from datetime import datetime, timedelta, timezone
from glob import glob
import re

import pandas as pd
from jinja2 import Template
# noinspection PyUnresolvedReferences
from psycopg2.errors import UndefinedTable
from sqlalchemy import create_engine, event, CursorResult
from sqlalchemy.engine import Row, RowMapping
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Any, Dict, Set, Tuple, Union, List


DB_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = Path(DB_DIR).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.config import CORE_CSET_TABLES, PG_DATATYPES_BY_GROUP, RECURSIVE_DEPENDENT_TABLE_MAP, \
    REFRESH_JOB_MAX_HRS, get_pg_connect_url
from backend.config import CONFIG, DATASETS_PATH, OBJECTS_PATH
from backend.utils import commify
from enclave_wrangler.models import pkey


DDL_JINJA_PATH_PATTERN = os.path.join(DB_DIR, 'ddl-*.jinja.sql')
TIMEZONE_DEFAULT = ['UTC/GMT', 'EST/EDT'][1]
DEBUG = False
DB = CONFIG["db"]
SCHEMA = CONFIG["schema"]


def dedupe_dicts(list_of_dicts: List[Dict]) -> List[Dict]:
    """Dedupe list of dictionaries"""
    # noinspection PyTypeChecker
    return list(map(dict, set(tuple(sorted(d.items())) for d in list_of_dicts)))


def extract_keys_from_nested_dict(d: Dict[str, Dict]) -> List[str]:
    """Extract keys from a nested dictionary.

    :return An ordered list in which the keys appear in the dictionary, walking
    through from top to bottom. If a key appears in the list multiple times, it
    will only appear once in the list, in the order in which it first appeared."""
    ordered_unique_keys = []
    def _extract_keys(d2):
        for k, v in d2.items():
            if k not in ordered_unique_keys:
                ordered_unique_keys.append(k)
            if isinstance(v, dict):
                _extract_keys(v)
    _extract_keys(d)
    return ordered_unique_keys


def get_dependent_tables_queue(independent_tables: Union[List[str], str], _filter: str = None) -> List[str]:
    """From independent_tables, get a list of all tables that depend on those tables.

    :param independent_tables:  The tables from which you are trying to get an ordered list of dependent tables from.
    This can be used in a situation such as: You are updating 1+ database tables 'root_tables', and now want to find
    which derived tables need to be updated in the correct order.
    :param _filter: One of 'table' or 'views'.
    :return: A list in the correct order such that for every entry in the list, any tables that depend on that entry
    will appear further down in the list.

    todo: Replace heuristic w/ a correct algorithm.
     I originally had no steps 2&3, and only 1&4 combined. But the result was out of order. This algorithm below is
     based on a quick (but messy/long) heuristic. Basically, the longer dependency trees go first. This corrected the
     problem that I had. But this is just a heuristic. I feel confident that there is some correct algorithm for this
     solvable in polynomial time.
    """
    if _filter not in [None, 'tables', 'views']:
        raise ValueError(f'Invalid _filter value: {_filter}. Must be one of "tables" or "views".')
    final_queue: List[str] = []
    table_queues1: List[List[str]] = []
    table_queues2: List[List[str]] = []
    queues_by_len: Dict[int, List[List[str]]] = {}
    independent_tables: List[str] = [independent_tables] if isinstance(independent_tables, str) else independent_tables

    # 1 & 4: Get a queue of dependent tables
    # 1. Build up a list of queues; queue is dependent tables
    for table in independent_tables:
        dependent_tree: Dict = RECURSIVE_DEPENDENT_TABLE_MAP.get(table, {})
        if not dependent_tree:
            continue
        q: List[str] = extract_keys_from_nested_dict(dependent_tree)
        table_queues1.append(q)

    # 2-3: Heuristic: Reorder the queue
    # 2. Group by queue lengths
    # - some dependency trees are the same for multiple tables; dedupe for simplicity
    table_queues1 = [list(x) for x in set([tuple(x) for x in table_queues1])]
    for q in table_queues1:
        l = len(q)
        if l not in queues_by_len:
            queues_by_len[l] = []
        queues_by_len[l].append(q)

    # 3. Reorganize list of queues, sorted by longest queues first
    queue_len_keys = list(queues_by_len.keys())
    queue_len_keys.sort(reverse=True)
    for k in queue_len_keys:
        queues: List[List[str]] = queues_by_len[k]
        for q in queues:
            table_queues2.append(q)

    # 4. Flatten to single list queue of dependent tables
    for q in table_queues2:
        for i in q:
            if i not in final_queue:
                final_queue.append(i)

    # 5. Optional: Filtering
    if _filter:
        views: List[str] = [x for x in list_views() if x in final_queue]
        if _filter == 'views':
            return views
        elif _filter == 'tables':
            return [x for x in final_queue if x not in views]

    return final_queue


def refresh_any_dependent_tables(con: Connection, independent_tables: List[str] = CORE_CSET_TABLES, schema=SCHEMA):
    """Refresh all derived tables that depend on independent_tables

    :param independent_tables: Any tables that changed for which we now want to update any dependent tables.
    """
    derived_tables: List[str] = get_dependent_tables_queue(independent_tables)
    if not derived_tables:
        print(f'No derived tables found for: {", ".join(independent_tables)}')
        return
    refresh_derived_tables_exec(con, derived_tables, schema)


def refresh_derived_tables_exec(
    con: Connection, derived_tables_queue: List[str], schema=SCHEMA
):
    """Refresh TermHub core cset derived tables

    This can also work to initially create the tables if they don't already exist.

    :param derived_tables_queue: Should be ordered such that for every entry in the list, any tables that depend on that
     entry will appear further down in the list."""
    temp_table_suffix = '_new'
    ddl_modules_queue = derived_tables_queue
    views = [x for x in list_views(schema=schema) if x in ddl_modules_queue]

    # Create new tables/views and backup old ones
    print('Derived tables')
    t0 = datetime.now()
    for module in ddl_modules_queue:
        t0_2 = datetime.now()
        print(f' - creating new table/view: {module}...')
        statements: List[str] = get_ddl_statements(schema, module, temp_table_suffix, 'flat')
        for statement in statements:
            try:
                run_sql(con, statement)
            except ProgrammingError as err:
                # Context: https://github.com/jhu-bids/TermHub/issues/792
                if schema == 'test_n3c' and 'does not exist for access method' in str(err):
                    print('Warning: A known error occurred while trying to create an extension-based index in the test'
                          ' schema. For now, we\'re skipping creation of this index here as is not necessary for '
                          'testing.', file=sys.stderr)
                    continue
                raise err
        # todo: warn if counts in _new table not >= _old table (if it exists)?
        run_sql(con, f'ALTER TABLE IF EXISTS {schema}.{module} RENAME TO {module}_old;')
        run_sql(con, f'ALTER TABLE {schema}.{module}{temp_table_suffix} RENAME TO {module};')
        print(f'   - completed in {(datetime.now() - t0_2).seconds} seconds')

    # Delete old tables/views. Because of view dependencies, order & commands are different
    print(f' - Removing older, temporarily backed up tables/views...')
    for view in views:
        ddl_modules_queue.remove(view)
        run_sql(con, f'DROP VIEW IF EXISTS {schema}.{view}_old;')

    for module in ddl_modules_queue:
        run_sql(con, f'DROP TABLE IF EXISTS {schema}.{module}_old;')
    t1 = datetime.now()
    print(f' - completed in {(t1 - t0).seconds} seconds')


# todo: move this somewhere else, possibly load.py or db_refresh.py
# todo: what to do if this process fails? any way to roll back? should we?
# todo: currently has no way of passing 'local' down to db status var funcs
# todo: last_derived_refresh_request and last_derived_refresh_exited: these should ideally be schema specific. That way,
#  refreshes on normal schema and test_schema don't block each other. Only a minor issue. Will sometimes cause tests
#  to take a very long time to run, especially during the wee hours when vocab/counts refreshes are running.
def refresh_derived_tables(
    con: Connection, independent_tables: List[str] = CORE_CSET_TABLES, schema=SCHEMA, local=False,
    polling_interval_seconds: int = 30
):
    """Refresh TermHub core cset derived tables: wrapper function

    Handles simultaneous requests and try/except for worker function: refresh_any_dependent_tables() ->
    refresh_derived_tables_exec()

    :param independent_tables: Any tables that changed for which we now want to update any dependent tables.
    """
    i = 0
    t0 = datetime.now()
    while True:
        i += 1
        if (datetime.now() - t0).total_seconds() >= 2 * 60 * 60:  # 2 hours
            raise RuntimeError('Timed out after waiting 2 hours for other active derived table refresh to complete.')
        # As of 2024/01/21 this is now a redundancy. Concerning the main refresh (refresh.py), it won't even begin if
        # ...the derived refresh is active.
        elif is_derived_refresh_active(local):
            print(f'Another derived table refresh is active. Waiting {polling_interval_seconds} seconds to try again.' \
                if i == 1 else '- trying again')
            time.sleep(polling_interval_seconds)
        else:
            try:
                update_db_status_var('last_derived_refresh_request', current_datetime(), local)
                refresh_any_dependent_tables(con, independent_tables, schema)
            finally:
                update_db_status_var('last_derived_refresh_exited', current_datetime(), local)
            break


# todo: Any use to having this? If not, remove. Otherwise, needs fixing. It was working when in get_db_connection() we
#  were not passing schema... but that's not really working. We need to be able to control the schema. After changing to
#  pass schema, sometimes it worked, and sometimes we got err: AttributeError: 'dict' object has no attribute 'cursor',
#  indicating that the kwargs weren't getting passed appropriately.
# from functools import partial
# from sqlalchemy.pool import QueuePool
# def set_search_path(dbapi_connection, schema=SCHEMA, connection_record=None):
#     """Set the search_path when connecting.
#
#     Source: https://chat.openai.com/share/0472ba44-0e58-44ad-bbcb-5eabffae3d39
#
#     Note: This hasn't helped w/ a problem we were having. If it continues to not help, we could rever to the old
#     version of get_db_connection().
#     """
#     cursor = dbapi_connection.cursor()
#     cursor.execute(f"SET SESSION search_path='{schema}'")
#     cursor.close()
#
#
# def get_db_connection(isolation_level='AUTOCOMMIT', schema: str = SCHEMA, local=False) -> Connection:
#     """Get database connection object
#
#     :param local: If True, connection is on local instead of production database.
#     """
#     if schema == None:
#         raise ValueError('Must pass schema to get_db_connection()')
#     engine = create_engine(
#         get_pg_connect_url(local),
#         poolclass=QueuePool,
#         isolation_level=isolation_level,
#     )
#     # event.listen(engine, "connect", set_search_path)
#     event.listen(engine, "connect", partial(set_search_path, {'schema': schema}))
#     return engine.connect()


# todo: make 'isolation_level' the final param, since we never override it. this would it so we dont' have to pass the
#  other params as named params.
def get_db_connection(isolation_level='AUTOCOMMIT', schema: str = SCHEMA, local=False) -> Connection:
    """Get DB connection object.

    :param local: If True, connection is on local instead of production database.
    """
    engine = create_engine(get_pg_connect_url(local), isolation_level=isolation_level)

    # noinspection PyUnusedLocal
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


def tz_datetime_str(dt: datetime, time_zone=TIMEZONE_DEFAULT) -> str:
    """Timezone-formatted datetime string"""
    if time_zone == 'UTC/GMT':
        stamp = dt.astimezone(timezone.utc).isoformat()
    elif time_zone == 'EST/EDT':
        stamp = dt.astimezone(pytz.timezone('America/New_York')).isoformat()
    else:
        raise ValueError(f'Unsupported time zone: {time_zone}')
    return stamp


def current_datetime(time_zone=TIMEZONE_DEFAULT) -> str:
    """Get current datetime in ISO format as a string."""
    return tz_datetime_str(datetime.now(), time_zone=time_zone)


def last_refresh_timestamp(con: Connection) -> str:
    """Get the timestamp of the last database refresh"""
    results: List[List] = sql_query(
        con, f"SELECT value FROM public.manage WHERE key = 'last_refresh_success';", return_with_keys=False)
    return results[0][0]


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
        results: List[List] = sql_query(con2, f"SELECT value FROM public.manage WHERE key = '{key}';", return_with_keys=False)
    last_updated = results[0][0] if results else None
    return last_updated and is_up_to_date(last_updated, skip_if_updated_within_hours)


def is_table_up_to_date(table_name: str, skip_if_updated_within_hours: int = None) -> bool:
    """Check if table is up to date"""
    if not skip_if_updated_within_hours:
        return False
    last_updated_key = f'last_updated_{table_name}'
    return check_if_updated(last_updated_key, skip_if_updated_within_hours)


def reset_refresh_status(local=False):
    """Reset DB refresh active status variables to reflect non-active status

    Used in situations where it is not active, but the variables reflect otherwise. This can happen due to exiting out
    of the debugger during a refresh or when a GH action times out.

    todo: consider also setting `last_refresh_result` to 'error' or 'termination', though if choosting 'error', then
     might want to set `last_refresh_error` to 'terminated' or 'unknown' or 'unknown; probably terminated'.
    """
    key_pairs = [
        ('last_derived_refresh_request', 'last_derived_refresh_exited'),
        ('last_refresh_request', 'last_refresh_exited')
    ]
    for start_time_key, end_time_key in key_pairs:
        last_start: datetime = dp.parse(check_db_status_var(start_time_key, local))
        last_end: datetime = dp.parse(check_db_status_var(end_time_key, local))
        if last_end < last_start:
            # arbitrarily add 1 microsecond so considered exited after start
            last_end: str = tz_datetime_str(last_start + timedelta(microseconds=1))
            update_db_status_var(end_time_key, last_end, local)
    update_db_status_var('refresh_status', 'inactive', local)


def reset_refresh_state(local=False):
    """Resets both temporary tables and status variables"""
    reset_temp_refresh_tables(local=local, verbose=False)
    reset_refresh_status(local)


def is_refresh_active(refresh_type=('standard', 'derived')[0], local=False, threshold=REFRESH_JOB_MAX_HRS) -> bool:
    """Checks if the database refresh is currently running

    As of 2023/10/28, there is still a variable called 'refresh_status' with values active/inactive, left there for
    convenience for manually checking the database. However, it does not serve any programmatic function. This variable
    was  problematic, because sometimes (e.g. when debugging), the process would exit abnormally and it wouldn't
    get set to 'inactive'. To circumvent that, 'last_start' and 'last_end' times are  now used. There is a 6 hour
    threshold to where if these variables show that the process is reported to have been running for that time, it is
    determined that this is in error and the refresh is considered inactive. 6 hours was chosen because this is the
    default maximum amount of time that a GitHub action can run, but it is also well over the normal amount of time that
    the refresh takes."""
    # Always check if derived tables refresh active for any case. Else check more for standard refresh status
    key_pairs = [('last_derived_refresh_request', 'last_derived_refresh_exited')]
    if refresh_type == 'standard':
        key_pairs = [('last_refresh_request', 'last_refresh_exited')] + key_pairs
    for start_time_key, end_time_key in key_pairs:
        # Check status
        last_start = dp.parse(check_db_status_var(start_time_key, local))
        last_end = dp.parse(check_db_status_var(end_time_key, local))
        # Determine if active
        considered_active_via_reported_time = last_start >= last_end
        hours_since_last_refresh: float = (dp.parse(current_datetime()) - last_end).total_seconds() / 60 / 60
        considered_active = considered_active_via_reported_time and hours_since_last_refresh < threshold
        if considered_active:
            return True
    return False


def is_derived_refresh_active(local=False) -> bool:
    """Check if any refreshing of the derived tables is active"""
    return is_refresh_active('derived', local)


# todo: Can update update_db_status_var() so that it can accept optional param 'con' to improve performance.
def update_db_status_var(key: str, val: str, local=False):
    """Update the `manage` table with information for a given variable, e.g. when a table was last updated"""
    with get_db_connection(schema='', local=local) as con:
        run_sql(con, f"DELETE FROM public.manage WHERE key = '{key}';")
        sql_str = f"INSERT INTO public.manage (key, value) VALUES (:key, :val);"
        run_sql(con, sql_str, {'key': key, 'val': val})


def check_db_status_var(key: str,  local=False):
    """Check the value of a given variable the `manage`table """
    with get_db_connection(schema='', local=local) as con:
        results: List = sql_query_single_col(con, f"SELECT value FROM public.manage WHERE key = '{key}';")
        return results[0] if results else None


def delete_db_status_var(key: str, local=False):
    """Delete information from the `manage` table """
    with get_db_connection(schema='', local=local) as con2:
        run_sql(con2, f"DELETE FROM public.manage WHERE key = '{key}';")


def insert_fetch_statuses(rows: List[Dict], local=False):
    """Update fetch status of record
    :param: rows: expects keys 'comment', 'primary_key', 'table', and 'status_initially'."""
    rows = [{k: str(v) for k, v in x.items()} for x in rows]  # corrects codeset_id from int to str
    with get_db_connection(schema='', local=local) as con:
        insert_from_dicts(con, 'fetch_audit', rows)


def select_failed_fetches(use_local_db=False) -> List[Dict]:
    """Collected data about unresolved fetches."""
    with get_db_connection(schema='', local=use_local_db) as con:
        return [dict(x) for x in sql_query(con, f"SELECT * FROM fetch_audit WHERE success_datetime IS NULL;")]


def fetch_status_set_success(rows: List[Dict], local=False):
    """Update fetch status of record
    :param rows: Takes the same format of list of dictionaries that you would get from select_failed_fetches()"""
    sql_str = """UPDATE fetch_audit
    SET success_datetime = current_timestamp, comment = :comment
    WHERE "table" = :table
      AND "primary_key" = :primary_key
      AND status_initially = :status_initially;"""
    with get_db_connection(schema='', local=local) as con:
        for row in rows:
            run_sql(con, sql_str, {k: v for k, v in row.items()})


def database_exists(con: Connection, db_name: str) -> bool:
    """Check if database exists"""
    result = run_sql(con, f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{db_name}';").fetchall()
    return len(result) == 1


def run_sql(con: Connection, query: str, params: Dict[str, Any] = {}) -> CursorResult:
    """Run a sql command"""
    query = text(query) if not isinstance(query, TextClause) else query
    return con.execute(query, params) if params else con.execute(query)


def sql_handle_none_to_null(query: str, params: Dict[str, Any], table: str, schema=SCHEMA) -> str:
    """Convert None to NULL for certain fields.

    SqlAlchemy w/ Postegres is finicky when accepting None as a NULL value for certain field types, e.g. numeric ones.
    Will find any numeric fields on table and convert None to NULL.
    """
    # Find numeric fields
    field_data_types: Dict[str, str] = get_field_data_types(table, schema)
    numeric_fields: Set[str] = set([k for k, v in field_data_types.items() if v in PG_DATATYPES_BY_GROUP['numeric']])
    # Figure out which fields need replacement
    fields_with_none: List[str] = [k for k, v in params.items() if v is None]
    # todo: this is really inefficient: O(n^2)
    numeric_fields_with_none: List[str] = []
    for fld1 in fields_with_none:
        for fld2 in numeric_fields:
            if fld1.startswith(fld2):
                numeric_fields_with_none.append(fld2)
                # numeric_fields.remove(fld2)  # would be performance optimization; but causes set size change err
    # Make replacements
    query2 = query
    for fld in numeric_fields_with_none:
        query2 = query2.replace(f'"{fld}" = v.{fld}',
            f'"{fld}" = CASE WHEN v.{fld}::text = \'None\' THEN NULL ELSE v.{fld}::double precision END')
    return query2


# todo: schema: Ideally, I should make sure that any usages of this function are passing `schema`.
def run_sql_update(
    con: Connection, query: str, params: Dict[str, Any] = {}, handle_none_as_null_on_table='', schema=SCHEMA
) -> CursorResult:
    """Run a sql update query

    :param handle_none_as_null_on_table: SqlAlchemy w/ Postegres is finicky when accepting None as a NULL value for
     certain field types, e.g. numeric ones. With this param, set the table name, and it will find any numeric fields
     and convert None to NULL. If passing this, should also pass schema.
    :param schema: Pass this with handle_none_as_null_on_table to ensure the correct table in the correct schema is
     being looked up.
    """
    if handle_none_as_null_on_table and None in params.values():
        query = sql_handle_none_to_null(query, params, handle_none_as_null_on_table, schema)
    return run_sql(con, query, params)


# todo: If we're only selecting from 1 column, do we want to modify this to return List[Any] instead of List[List]?
def sql_query(
    con: Connection, query: Union[text, str], params: Dict = {}, debug: bool = DEBUG, return_with_keys=True
) -> Union[List[RowMapping], List[List[Any]]]:
    """Run an idempotent (read) SQL query with optional params, fetching records.
    Inspiration:
      https://stackoverflow.com/a/39414254/1368860:
      query = "SELECT * FROM my_table t WHERE t.id = ANY(:ids);"
      conn.execute(sqlalchemy.text(query), ids=some_ids)
    """
    try:
        q: CursorResult = run_sql(con, query, params)

        if debug:
            print(f'{query}\n{json.dumps(params, indent=2)}')
        # Conversions: after upgrading some packages, fastapi can no longer serialize Row & RowMapping objects
        # todo: format q.mappings() for FastAPI like w/ q.fetchall() below? Are we not doing this cuz heavy refactor?
        if return_with_keys:
            # noinspection PyTypeChecker
            results: List[RowMapping] = q.mappings().all()  # Key value pairs
            # return [dict(x) for x in results]
            return results
        else:
            # noinspection PyTypeChecker
            results: List[Row] = q.fetchall()  # Row tuples, with additional properties
            return [list(x) for x in results]
    except (ProgrammingError, OperationalError) as err:
        raise RuntimeError(
            f'Got an error [{err}] executing the following statement:\n{query}, {json.dumps(params, indent=2)}')


def sql_query_single_col(*argv) -> List:
    """Run SQL query on single column"""
    results: List = sql_query(*argv, return_with_keys=False)
    return [r[0] for r in results]


def delete_obj_by_composite_key(con, table: str, key_ids: Dict[str, Union[str, int]]):
    """Get object by ID"""
    keys_str = ' AND '.join([f'{key} = (:{key})' for key in key_ids.keys()])
    return run_sql(
        con, f'DELETE FROM {table} WHERE {keys_str}',
        {f'{key}': _id for key, _id in key_ids.items()})


def get_obj_by_composite_key(con, table: str, keys: List[str], obj: Dict) -> List[RowMapping]:
    """Get object by ID
    todo: could be made more consistent w/ get_obj_by_id(): accept obj_id instead?"""
    keys_str = ' AND '.join([f'"{key}" = (:{key}_id)' for key in keys])
    return sql_query(
        con, f'SELECT * FROM {table} WHERE {keys_str}',
        {f'{key}_id': obj[key] for key in keys})


def get_obj_by_id(con, table: str, pk: str, obj_id: Union[str, int]) -> List[List]:
    """Get object by ID"""
    return sql_query(con, f'SELECT * FROM {table} WHERE {pk} = (:obj_id)', {'obj_id': obj_id}, return_with_keys=False)


def get_objs_by_id(con, table: str, pk: str, obj_ids: List[Union[str, int]]) -> List[Dict]:
    """Get database records by their IDs
    todo: refactor: look to insert_from_dicts() more secure way to do this by passing `params` to run_sql()`
    :return: dictionary with keys as the primary key and values as the row contents"""
    results: List[RowMapping] = sql_query(
        con, f'SELECT * FROM {table} WHERE {pk} {sql_in(obj_ids, True)}', return_with_keys=True)
    return [dict(x) for x in results]


def get_objs_by_composite_key(con, table: str, keys: List[str], objs: List[Dict]) -> List[Dict]:
    """Get database records by their IDs
    todo: could be made more consistent w/ get_objs_by_id(): accept objs_ids instead?
    todo: refactor: look to insert_from_dicts() more secure way to do this by passing `params` to run_sql()`
    :return: dictionary with keys as the primary key and values as the row contents"""
    key_vals = {key: [str(obj[key]) for obj in objs] for key in keys}
    conditions = ' AND '.join([f'"{k}" {sql_in(v, True)}' for k, v in key_vals.items()])
    query = f"SELECT * FROM {table} WHERE {conditions};"
    results: List[RowMapping] = sql_query(con, query, return_with_keys=True)
    return [dict(x) for x in results]


def get_concept_set_members_rows(
    con: Connection, codeset_id__concept_id__pairs: List[Tuple[int, int]]
) -> List[Dict]:
    """Get rows from concept_set_members given IDs
    todo: too specific to be in utils.py? move?"""
    objs = [{'codeset_id': pair[0], 'concept_id': pair[1]} for pair in codeset_id__concept_id__pairs]
    return get_objs_by_composite_key(con, 'concept_set_members',['codeset_id', 'concept_id'], objs)


def get_cset_members_items_rows(
    con: Connection, codeset_id__concept_id__pairs: List[Tuple[int, int]]
) -> List[Dict]:
    """Get rows from cset_members_items given IDs
    todo: too specific to be in utils.py? move?"""
    objs = [{'codeset_id': pair[0], 'concept_id': pair[1]} for pair in codeset_id__concept_id__pairs]
    return get_objs_by_composite_key(con, 'cset_members_items', ['codeset_id', 'concept_id'], objs)


def fix_jagged_rows(rows: List[Dict]) -> List[Dict]:
    """# Fix possible jaggedneess / missing fields in rows"""
    fields = []
    for row in rows:
        fields.extend(row.keys())
        for k in row.keys():
            fields.append(k)
    fields = set(fields)
    return [{field: row.get(field, None) for field in fields} for row in rows]


def update_from_dicts(con: Connection, table: str, rows: List[Dict]):
    """Update rows in table from a list of dictionaries"""
    pk: str = pkey(table)
    rows = fix_jagged_rows(rows)
    # todo: fully use parameterized queries to prevent SQL injection
    key_vals: Dict[str, Any] = key_vals_for_sqlalchemy_query(rows)
    values: str = value_str_for_sqlalchemy_query(rows)
    fields: str = ', '.join([f'"{x}"' for x in rows[0].keys()])
    field_set_str: str= ', '.join([f'"{x}" = v.{x}' for x in [x for x in rows[0].keys() if x != pk]])
    statement = f"""
        UPDATE {table}
        SET {field_set_str}
        FROM (VALUES
            {values}
        ) AS v({fields})
        WHERE {table}.{pk} = v.{pk};"""
    run_sql_update(con, statement, key_vals, handle_none_as_null_on_table=table)


def key_vals_for_sqlalchemy_query(rows: List[Dict]) -> Dict[str, Any]:
    """Get key value pairs  for a non-idempotent SQL query."""
    return {f'{k}{i}': v for i, d in enumerate(rows) for k, v in d.items()}


def value_str_for_sqlalchemy_query(rows: List[Dict]) -> str:
    """Get a string of values for a non-idempotent SQL query."""
    return  ', '.join([f"({', '.join([':' + str(k) + str(i) for k in d.keys()])})" for i, d in enumerate(rows)])

def insert_from_dicts(con: Connection, table: str, rows: List[Dict], skip_if_already_exists=True):
    """Insert rows into table from a list of dictionaries"""
    pk: str = pkey(table)
    if skip_if_already_exists:
        if pk and isinstance(pk, str):  # normal, single primary key
            already_in_db: List[Dict] = get_objs_by_id(con, table, pk, [row[pk] for row in rows])
            already_in_db_ids = set([row[pk] for row in already_in_db])
            rows = [row for row in rows if row[pk] not in already_in_db_ids]
        elif pk and isinstance(pk, list):  # composite key
            already_in_db: List[Dict] = get_objs_by_composite_key(con, table, pk, rows)
            already_in_db_ids = [[row[pk_n] for pk_n in pk] for row in already_in_db]
            rows = [row for row in rows if [row[pk_n] for pk_n in pk] not in already_in_db_ids]
    if rows:
        rows = fix_jagged_rows(rows)
        # todo: fully use parameterized queries to prevent SQL injection
        key_vals: Dict[str, Any] = key_vals_for_sqlalchemy_query(rows)
        values: str = value_str_for_sqlalchemy_query(rows)
        statement = f"""INSERT INTO {table} ({', '.join([f'"{x}"' for x in rows[0].keys()])}) VALUES {values}"""
        run_sql(con, statement, key_vals)


def insert_from_dict(con: Connection, table: str, d: Union[Dict, List[Dict]], skip_if_already_exists=True):
    """Insert row into table from a dictionary"""
    if isinstance(d, list):
        return insert_from_dicts(con, table, d, skip_if_already_exists)
    if skip_if_already_exists:  # todo: simplify logic as in insert_from_dicts()
        pk: str = pkey(table)
        if pk:
            already_in_db = []
            if isinstance(pk, str):  # normal, single primary key
                already_in_db: List[List] = get_obj_by_id(con, table, pk, d[pk])
            elif isinstance(pk, list):  # composite key
                already_in_db: List[RowMapping] = get_obj_by_composite_key(con, table, pk, d)
            if already_in_db:
                return
    query = f"""
    INSERT INTO {table} ({', '.join([f'"{x}"' for x in d.keys()])})
    VALUES ({', '.join([':' + str(k) for k in d.keys()])})"""
    run_sql(con, query, d)


def sql_count(con: Connection, table: str) -> int:
    """Return the number of rows in a table. A simple count of rows, not ignoring NULLs or duplicates."""
    query = f'SELECT COUNT(*) FROM {table};'
    results: List[List] = sql_query(con, query, return_with_keys=False)
    return results[0][0]


def sql_in(lst: Union[List, Set], quote_items=False) -> str:
    """Construct SQL 'IN' expression."""
    if quote_items:
        lst = [str(x).replace("'", "''") for x in lst]
        s: str = ', '.join([f"'{x}'" for x in lst]) or 'NULL'
    else:
        s: str = ', '.join([str(x) for x in lst]) or 'NULL'
    return f' IN ({s}) '

def sql_in_safe(lst: List) -> (str, dict):
    """Safe version of SQL 'in' statement."""
    bindparams = [":id{}".format(i) for i in range(len(lst))]
    query = text(','.join(bindparams))
    params = {"id{}".format(i): _id for i, _id in enumerate(lst)}
    return query, params


def list_schema_objects(
    con: Connection = None, schema: str = None, filter_views=False, filter_sequences=False,
    filter_temp_refresh_objects=False, filter_tables=False, names_only=False, verbose=True
) -> Union[List[Row], List[str]]:
    """Show tables

    :param filter_temp_refresh_objects: Filters out any temporary tables/views that are created during the refresh, e.g.
     ones that end w/ the suffix '_old' or '_new'.
    """
    if con and schema:
        raise ValueError('`con` and `schema` params should not both be passed; choose one')
    schema = SCHEMA if not schema else schema
    conn = con if con else get_db_connection(schema=schema)
    # Query
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
    res: List[List] = sql_query(conn, query, return_with_keys=False)
    if not con:
        conn.close()
    # Filter
    if filter_tables:
        res = [x for x in res if x[2] != 'table']
    if filter_views:
        res = [x for x in res if x[2] != 'view']
    if filter_sequences:
        res = [x for x in res if x[2] != 'sequence']
    if filter_temp_refresh_objects:
        res = [x for x in res if not x[1].endswith('_new') and not x[1].endswith('_old')]
    # Print
    if verbose:
        print(pd.DataFrame(res))
        # print('\n'.join([', '.join(r) for r in res])) ugly
        # print(pdump(res)) doesn't work
    # Format
    if names_only:
        res: List[str] = [x[1] for x in res]
    return res


def list_views(con: Connection = None, schema: str = None, filter_temp_refresh_views=False) -> List[str]:
    """Get list of names of views in schema"""
    return list_schema_objects(con, schema, False, True, filter_temp_refresh_views, True, True, False)


def load_csv(
    con: Connection, table: str, table_type: str = ['dataset', 'object'][0], replace_rule='replace if diff row count',
    schema: str = SCHEMA, is_test_table=False, local=False, optional_suffix='', path_override: Union[Path, str] = None
):
    """Load CSV into table
    :param replace_rule:
        - 'replace if diff row count'
        - 'do not replace'
        - 'finish aborted upload'   # useful if load_csv crashes before uploading the whole dataframe

      First, will replace table (that is, truncate and load records; will fail if table cols have changed, i think
     'do not replace'  will create new table or load table if table exists but is empty
    :param optional_suffix: Useful for when remaking tables when database is live. For example, you can upload a new
    'concept' table using the suffix '_new', then after 'concept_new' is successfully loaded, you can delete the old
    table and rename this table as just 'concept'.

    - Uses: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    """
    table_name_no_suffix = table
    table = table + optional_suffix
    # Edge cases
    existing_rows = 0
    try:
        r = con.execute(text(f'select count(*) from {schema}.{table}'))
        existing_rows = r.one()[0]
    except Exception as err:
        # noinspection PyUnresolvedReferences
        if isinstance(err.orig, UndefinedTable):
            print(f'INFO: {schema}.{table} does not not exist; will create it')
        else:
            raise err

    if replace_rule == 'do not replace' and existing_rows > 0:
        print(f'INFO: {schema}.{table} exists with {commify(existing_rows)} rows; leaving it')
        return

    # Load table
    path = path_override if path_override else os.path.join(DATASETS_PATH, f'{table_name_no_suffix}.csv') \
        if table_type == 'dataset' else os.path.join(OBJECTS_PATH, table, 'latest.csv')
    if not os.path.isfile(path):
        print(f'INFO: {path} does not exist; skipping')
        return
    df = pd.read_csv(path)

    # todo: this could be replaced by using path_override and saving some static files with 1 line
    if is_test_table and not path_override:
        df = df.head(1)

    print(f'INFO: loading {schema}.{table} ({len(df)} rows) into {CONFIG["server"]}:{DB}')
    if replace_rule == 'replace if diff row count' and existing_rows == len(df):
        print(f'INFO: {schema}.{table} exists with same number of rows {existing_rows}; leaving it')
        return
    if replace_rule == 'finish aborted upload' and existing_rows < len(df):
        print(f'INFO: {schema}.{table} exists with {commify(existing_rows)} rows; uploading remaining {commify(len(df)-existing_rows)} rows')
        df = df.iloc[existing_rows: len(df)]
    else:
        con.execute(text(f'DROP TABLE IF EXISTS {schema}.{table} CASCADE'))

    # - load
    df.to_sql(table, con, **{'if_exists': 'append', 'index': False, 'schema': schema, 'chunksize': 1000})
    # - update status
    if not is_test_table:
        update_db_status_var(f'last_updated_{table_name_no_suffix}', str(current_datetime()), local)


def get_field_data_types(table: str, schema=SCHEMA) -> Dict[str, str]:
    """Get data types for each field in the table"""
    with get_db_connection(schema='') as con:
        field_data_types: List[Dict[str, str]] = [dict(x) for x in sql_query(con, f"""
            SELECT column_name,  data_type FROM information_schema.columns 
            WHERE table_schema = '{schema}' AND table_name = '{table}';""")]
        field_data_types: Dict[str, str] = {x['column_name']: x['data_type'] for x in field_data_types}
    return field_data_types


def list_tables(con: Connection = None, schema: str = None, filter_temp_refresh_tables=False) -> List[str]:
    """List table names in schema"""
    return list_schema_objects(con, schema, True, True, filter_temp_refresh_tables, names_only=True, verbose=False)


def get_ddl_statements(
    schema: str = SCHEMA, modules: Union[List[str], str] = None, table_suffix='', return_type=['flat', 'nested'][1],
    unique_index_names=True,
) -> Union[List[str], Dict[str, List[str]]]:
    """From local SQL DDL Jinja2 templates, pa rse and get a list of SQL statements to run.

    :param: modules: DDL files follow the naming schema `ddl-ORDER_NUMBER-MODULE_NAME.jinja.sql`. If `modules` is
    provided, will only return statements for those modules. If not provided, will return all statements.
    :param table_suffix: Used by DB refresh. This is used by a subset of the DDL modules. The use case here is that in
    order to refresh the DB, rather than doing inserts on existing derived tables, we re-run the DDL to create new
    tables with a suffix, then drop the original and rename the one we just created to remove the suffix.

    todo's
      1. For each table: don't do anything if these tables exist & initialized
      2. Add alters to fix data types (although, should really move this stuff to dtypes settings when creating
      dataframe that loads data into db.
      3. I think it's inserting a second ; at the end of the last statement of a given module
      4. consider throwing an error if no statements found, either here, or where func is called
    """
    modules: List[str] = [modules] if isinstance(modules, str) else modules
    index_suffix: str = '' if not unique_index_names else '_' + str(randint(10000000, 99999999))
    paths: List[str] = glob(DDL_JINJA_PATH_PATTERN)
    if modules:
        paths = [p for p in paths if any([m == os.path.basename(p).split('-')[2].split('.')[0] for m in modules])]
    paths = sorted(paths, key=lambda x: int(os.path.basename(x).split('-')[1]))
    statements: List[str] = []
    statements_by_module: Dict[str, List[str]] = {}
    for i, path in enumerate(paths):
        with open(path, 'r') as file:
            template_str = file.read()
        module = os.path.basename(path).split('-')[2].split('.')[0]
        ddl_text = Template(template_str).render(
            schema=schema + '.', optional_suffix=table_suffix, optional_index_suffix=index_suffix)
        without_comments = re.sub(r'^\s*--.*\n*', '', ddl_text, flags=re.MULTILINE)
        # Each DDL file should have 1 or more statements separated by an empty line (two line breaks).
        module_statements = [x + ';' for x in without_comments.split(';\n\n')]
        if return_type == 'flat':
            statements.extend(module_statements)
        elif return_type == 'nested':
            statements_by_module[f'{i+1}-{module}'] = module_statements
    return statements if return_type == 'flat' else statements_by_module


def delete_codesets_from_db(codeset_ids):
    """ Delete codesets from db
        todo: finish working on this. addresses: https://github.com/jhu-bids/termhub/issues/571
          for each codeset_id will need to:
            - get concept_set_name
            - delete record from code_sets table
            - delete associated concept_set_members and concept_set_version_item records
            - determine whether container has any remaining code_sets (versions)
              attached to it, if not, delete container
            - regenerate derived tables (all_csets, csets_members_items, etc.)
    """
    with get_db_connection() as con:
        # todo: finish working on, then remove noinspection
        # noinspection PyUnusedLocal
        code_sets_to_be_deleted = sql_query(
            con, f"""SELECT codeset_id, concept_set_name FROM code_sets WHERE id IN ({codeset_ids.sql_format()})"""
        )


def reset_temp_refresh_tables(schema: str = SCHEMA, local=False, verbose=True):
    """This is run if an error occurs while refreshing tables, and resets to their state before the refresh."""
    if verbose:
        print('Error occurred during table refresh. Resetting tables to pre-refresh state; restoring backups.',
              file=sys.stderr)
    with get_db_connection(schema=schema, local=local) as con:
        for item_type, func in (('VIEW', list_views), ('TABLE', list_tables)):
            # Get all tables/views
            items: List[str] = func(con)
            # _old tables/views
            #  - For each, drop the current one and replace w/ the backed up one. Drop and remake any dependent views.
            backed_up_items = [t for t in items if t.endswith('_old')]
            for item in backed_up_items:
                item = item.replace('_old', '')
                dependent_views: List[str] = get_dependent_tables_queue(item, 'views')
                for view in dependent_views:
                    run_sql(con, f'DROP VIEW IF EXISTS {schema}.{view};')  # alternative: drop table w/ CASCADE
                run_sql(con, f'DROP {item_type} IF EXISTS {schema}.{item};')
                run_sql(con, f'ALTER {item_type} {schema}.{item}_old RENAME TO {item};')
                for view in dependent_views:
                    statements: List[str] = get_ddl_statements(schema, view, return_type='flat')
                    for statement in statements:
                        run_sql(con, statement)
            # _new tables/views
            dangling_new_items = [t for t in items if t.endswith('_new')]
            for item in dangling_new_items:
                item = item.replace('_new', '')
                if item in items:
                    run_sql(con, f'DROP {item_type} {schema}.{item}_new;')
                else:  # not sure if this would ever happen. never seen it happen. if so it will err if name collision
                    run_sql(con, f'ALTER {item_type} {schema}.{item}_new RENAME TO {item};')


def get_idle_connections(interval: str = '1 week'):
    """Get information about any currently idle connections

    :param: interval: See https://www.postgresql.org/docs/current/functions-datetime.html

    todo: consider backend_start vs query_start; backend probably better
    backend_start: This field indicates the timestamp when the database backend process for a particular connection was
    started. It provides information about when the connection to the database was established.
    query_start: This field represents the timestamp when the currently executing query for a connection started. If a
    connection is idle, this field will be null. When a query is actively being processed, this field reflects the start
    time of that query."""
    query = f"SELECT * FROM pg_stat_activity WHERE state = 'idle' AND backend_start > now() - f'{interval}'::interval;"
    with get_db_connection(schema='') as con:
        result = [dict(x) for x in sql_query(con, query)]
    return result


def kill_idle_cons(threshold_minutes=10):
    """Kill idle connections older than threshold minutes

    Kills only those connections having to do with TermHub."""
    qry = f"""SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
    WHERE state = 'idle' and datname = 'termhub' and usename = 'thadmin' 
    and state_change < NOW() - INTERVAL '{threshold_minutes} minutes';
    """
    with get_db_connection(schema='') as con:
        run_sql(con, qry)


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='termhub-db-utils', description='Database utilities.')
    parser.add_argument(
        '-f', '--reset-refresh-state', required=False, default=False, action='store_true',
        help='Resets both temporary tables and status variables')
    parser.add_argument(
        '-k', '--kill-idle-cons', required=False, default=False, action='store_true',
        help='Kills any idle connections older than 10 minutes')
    d: Dict = vars(parser.parse_args())
    if d['kill_idle_cons']:
        print('Killing idle connections older than 10 minutes')
        kill_idle_cons()
    if d['reset_refresh_state']:
        print('Resetting temporary tables and status variables')
        reset_refresh_state()


if __name__ == '__main__':
    cli()
