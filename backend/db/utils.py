"""Utils for database usage

todo's
  1. Some functions could be improved using `sql_query()` `params` arg to be less prone to sql injection.
"""
import json
import os
import time
from random import randint

import pytz
import dateutil.parser as dp
from datetime import datetime, timezone
from glob import glob
import re

import pandas as pd
from jinja2 import Template
# noinspection PyUnresolvedReferences
from psycopg2.errors import UndefinedTable
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Row, RowMapping
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.sql.elements import TextClause
from typing import Any, Dict, Tuple, Union, List

from backend.db.config import CONFIG, CORE_CSET_DEPENDENT_TABLES, CORE_CSET_TABLES, DATASETS_PATH, DDL_JINJA_PATH_PATTERN, \
    OBJECTS_PATH, \
    RECURSIVE_DEPENDENT_TABLE_MAP, VIEWS, get_pg_connect_url
from backend.utils import commify
from enclave_wrangler.models import pkey

DEBUG = False
DB = CONFIG["db"]
SCHEMA = CONFIG["schema"]


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


def get_dependent_tables_queue(independent_tables: List[str]) -> List[str]:
    """From independent_tables, get a list of all tables that depend on those tables.

    :param independent_tables:  The tables from which you are trying to get an ordered list of dependent tables from.
    This can be used in a situation such as: You are updating 1+ database tables 'root_tables', and now want to find
    which derived tables need to be updated in the correct order.
    :return: A list in the correct order such that for every entry in the list, any tables that depend on that entry
    will appear further down in the list.

    todo: Replace heuristic w/ a correct algorithm.
     I originally had no steps 2&3, and only 1&4 combined. But the result was out of order. This algorithm below is
     based on a quick (but messy/long) heuristic. Basically, the longer dependency trees go first. This corrected the
     problem that I had. But this is just a heuristic. I'm feel confident that there is some correct algorithm for this
     solvable in polynomial time. When this is done, probably should delete CORE_CSET_DEPENDENT_TABLES & its usages."""
    final_queue: List[str] = []
    table_queues1: List[List[str]] = []
    table_queues2: List[List[str]] = []
    queues_by_len: Dict[int, List[List[str]]] = {}

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

    return final_queue


def refresh_any_dependent_tables(con: Connection, independent_tables: List[str] = CORE_CSET_TABLES, schema=SCHEMA):
    """Refresh all derived tables that depend on independent_tables"""
    derived_tables: List[str] = get_dependent_tables_queue(independent_tables)
    if not derived_tables:
        print(f'No derived tables found for: {", ".join(independent_tables)}')
    refresh_derived_tables(con, derived_tables, schema)


def refresh_derived_tables(
    con: Connection, derived_tables_queue: List[str] = CORE_CSET_DEPENDENT_TABLES, schema=SCHEMA
):
    """Refresh TermHub core cset derived tables

    This can also work to initially create the tables if they don't already exist.

    :param derived_tables_queue: Should be ordered such that for every entry in the list, any tables that depend on that
     entry will appear further down in the list."""
    temp_table_suffix = '_new'
    ddl_modules_queue = derived_tables_queue
    views = [x for x in VIEWS if x in ddl_modules_queue]

    # Create new tables and backup old ones
    print('Derived tables')
    t0 = datetime.now()
    hash_num = '_' + str(randint(10000000, 99999999))
    for module in ddl_modules_queue:
        print(f' - creating new table/view: {module}...')
        statements: List[str] = get_ddl_statements(schema, [module], temp_table_suffix, hash_num, 'flat')
        for statement in statements:
            run_sql(con, statement)
        # todo: warn if counts in _new table not >= _old table (if it exists)?
        run_sql(con, f'ALTER TABLE IF EXISTS {schema}.{module} RENAME TO {module}_old;')
        run_sql(con, f'ALTER TABLE {schema}.{module}{temp_table_suffix} RENAME TO {module};')

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
def refresh_termhub_core_cset_derived_tables(con: Connection, schema=SCHEMA, polling_interval_seconds: int = 30):
    """Refresh TermHub core cset derived tables: wrapper function

    Handles simultaneous requests and try/except for worker function: refresh_termhub_core_cset_derived_tables_exec()"""
    i = 0
    t0 = datetime.now()
    while True:
        i += 1
        if (datetime.now() - t0).total_seconds() >= 2 * 60 * 60:  # 2 hours
            raise RuntimeError('Timed out after waiting 2 hours for other active derived table refresh to complete.')
        elif check_db_status_var('derived_tables_refresh_status') == 'active':
            msg = f'Another derived table refresh is active. Waiting {polling_interval_seconds} seconds to try again.' \
                if i == 0 else '- trying again'
            print(msg)
            time.sleep(polling_interval_seconds)
        else:
            try:
                update_db_status_var('derived_tables_refresh_status', 'active')
                # The following two calls yield equivalent results as of 2023/08/08. I've commented out
                #  refresh_derived_tables() in case anything goes wrong with refresh_any_dependent_tables(), since that
                #  is based on a heuristic currently, and if anything goes wrong, we may want to switch back. -joeflack4
                # refresh_derived_tables(con, CORE_CSET_DEPENDENT_TABLES, schema)
                refresh_any_dependent_tables(con, CORE_CSET_TABLES, schema)
            finally:
                update_db_status_var('derived_tables_refresh_status', 'inactive')
            break


# todo: make 'isolation_level' the final param, since we never override it. this would it so we dont' have to pass the
#  other params as named params.
def get_db_connection(isolation_level='AUTOCOMMIT', schema: str = SCHEMA, local=False) -> Connection:
    """Connect to db
    :param local: If True, connection is on local instead of production database."""
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


def current_datetime(time_zone=['UTC/GMT', 'EST/EDT'][1]) -> str:
    """Get current datetime in ISO format as a string."""
    if time_zone == 'UTC/GMT':
        stamp = datetime.now(timezone.utc).isoformat()
    elif time_zone == 'EST/EDT':
        stamp = datetime.now(pytz.timezone('America/New_York')).isoformat()
    else:
        raise ValueError(f'Unsupported time zone: {time_zone}')
    return stamp


def last_refresh_timestamp(con: Connection) -> str:
    """Get the timestamp of the last database refresh"""
    return sql_query(
        con, f"SELECT value FROM public.manage WHERE key = 'last_refresh_success';", return_with_keys=False)[0][0]


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
        results = sql_query(con2, f"SELECT value FROM public.manage WHERE key = '{key}';", return_with_keys=False)
    last_updated = results[0][0] if results else None
    return last_updated and is_up_to_date(last_updated, skip_if_updated_within_hours)


def is_table_up_to_date(table_name: str, skip_if_updated_within_hours: int = None) -> bool:
    """Check if table is up to date"""
    if not skip_if_updated_within_hours:
        return False
    last_updated_key = f'last_updated_{table_name}'
    return check_if_updated(last_updated_key, skip_if_updated_within_hours)

# todo: Can update update_db_status_var() so that it can accept optional param 'con' to improve performance.
def update_db_status_var(key: str, val: str, local=False):
    """Update the `manage` table with information for a given variable, e.g. when a table was last updated
    todo: change to a 1-liner UPDATE statement"""
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


def sql_query(
    con: Connection, query: Union[text, str], params: Dict = {}, debug: bool = DEBUG, return_with_keys=True
) -> Union[List[RowMapping], List[Row]]:
    """Run a sql query with optional params, fetching records.
    https://stackoverflow.com/a/39414254/1368860:
    query = "SELECT * FROM my_table t WHERE t.id = ANY(:ids);"
    conn.execute(sqlalchemy.text(query), ids=some_ids)
    """
    query = text(query) if not isinstance(query, TextClause) else query
    try:
        if params:
            # after SQLAlchemy upgrade, send params as dict, not **params
            q = con.execute(query, params) if params else con.execute(query)
        else:
            q = con.execute(query)

        if debug:
            print(f'{query}\n{json.dumps(params, indent=2)}')
        if return_with_keys:
            # noinspection PyTypeChecker
            results: List[RowMapping] = q.mappings().all()  # key value pairs
        else:
            # noinspection PyTypeChecker
            results: List[Row] = q.fetchall()  # Row tuples, with additional properties
        return results
    except (ProgrammingError, OperationalError) as err:
        raise RuntimeError(f'Got an error [{err}] executing the following statement:\n{query}, {json.dumps(params, indent=2)}')


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


def get_obj_by_id(con, table: str, pk: str, obj_id: Union[str, int]) -> List[Row]:
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


def insert_from_dicts(con: Connection, table: str, rows: List[Dict], skip_if_already_exists=True):
    """Insert rows into table from a list of dictionaries"""
    pk: str = pkey(table)
    if skip_if_already_exists:
        if pk and isinstance(pk, str):  # normal, single primary key
            already_in_db: List[Dict] = get_objs_by_id(con, table, pk, [row[pk] for row in rows])
            already_in_db_ids = [row[pk] for row in already_in_db]
            rows = [row for row in rows if row[pk] not in already_in_db_ids]
        elif pk and isinstance(pk, list):  # composite key
            already_in_db: List[Dict] = get_objs_by_composite_key(con, table, pk, rows)
            already_in_db_ids = [[row[pk_n] for pk_n in pk] for row in already_in_db]
            rows = [row for row in rows if [row[pk_n] for pk_n in pk] not in already_in_db_ids]

    if rows:
        # Fix possible jaggedneess / missing fields in rows
        fields = []
        for row in rows:
            fields.extend(row.keys())
            for k in row.keys():
                fields.append(k)
        fields = set(fields)
        rows = [{field: row.get(field, None) for field in fields} for row in rows]
        key_vals = {f'{k}{i}': v for i, d in enumerate(rows) for k, v in d.items()}
        values = ', '.join([f"({', '.join([':' + str(k) + str(i) for k in d.keys()])})" for i, d in enumerate(rows)])
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
                already_in_db: List[Dict] = get_obj_by_id(con, table, pk, d[pk])
            elif isinstance(pk, list):  # composite key
                already_in_db: List[Dict] = get_obj_by_composite_key(con, table, pk, d)
            if already_in_db:
                return

    insert = f"""
    INSERT INTO {table} ({', '.join([f'"{x}"' for x in d.keys()])})
    VALUES ({', '.join([':' + str(k) for k in d.keys()])})"""
    run_sql(con, insert, d)


def sql_count(con: Connection, table: str) -> int:
    """Return the number of rows in a table. A simple count of rows, not ignoring NULLs or duplicates."""
    query = f'SELECT COUNT(*) FROM {table};'
    return sql_query(con, query, return_with_keys=False)[0][0]


def sql_in(lst: List, quote_items=False) -> str:
    """Construct SQL 'IN' expression."""
    if quote_items:
        lst = [str(x).replace("'", "''") for x in lst]
        s: str = ', '.join([f"'{x}'" for x in lst]) or 'NULL'
    else:
        s: str = ', '.join([str(x) for x in lst]) or 'NULL'
    return f' IN ({s}) '


def run_sql(con: Connection, command: str, params: Dict = {}) -> Any:
    """Run a sql command"""
    command = text(command) if not isinstance(command, TextClause) else command
    if params:
        q = con.execute(command, params) if params else con.execute(command)
    else:
        q = con.execute(command)
    return q


def sql_query_single_col(*argv) -> List:
    """Run SQL query on single column"""
    results = sql_query(*argv, return_with_keys=False)
    return [r[0] for r in results]


def show_tables(con: Connection = None, print_dump=True):
    """Show tables"""
    con = con if con else get_db_connection()
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
    res = sql_query(con, query, return_with_keys=False)
    if print_dump:
        print(pd.DataFrame(res))
        # print('\n'.join([', '.join(r) for r in res])) ugly
        # print(pdump(res)) doesn't work
    return res


def load_csv(
    con: Connection, table: str, table_type: str = ['dataset', 'object'][0], replace_rule='replace if diff row count',
    schema: str = SCHEMA, is_test_table=False, local=False, optional_suffix=''
):
    """Load CSV into table
    :param replace_rule: 'replace if diff row count' or 'do not replace'
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
    path = os.path.join(DATASETS_PATH, f'{table_name_no_suffix}.csv') if table_type == 'dataset' \
        else os.path.join(OBJECTS_PATH, table, 'latest.csv')
    df = pd.read_csv(path)

    if is_test_table:
        df = df.head(1)

    if replace_rule == 'replace if diff row count' and existing_rows == len(df):
        print(f'INFO: {schema}.{table} exists with same number of rows {existing_rows}; leaving it')
        return

    print(f'INFO: \nloading {schema}.{table} into {CONFIG["server"]}:{DB}')
    # Clear data if exists
    try:
        con.execute(text(f'DROP TABLE {schema}.{table} CASCADE'))
    except ProgrammingError:
        pass

    # Load
    # `schema='termhub_n3c'`: Passed so Joe doesn't get OperationalError('(pymysql.err.OperationalError) (1050,
    #  "Table \'code_sets\' already exists")')
    #  https://stackoverflow.com/questions/69906698/pandas-to-sql-gives-table-already-exists-error-with-if-exists-append
    kwargs = {'if_exists': 'append', 'index': False, 'schema': schema}
    # TODO: add suffix
    df.to_sql(table, con, **kwargs)

    update_db_status_var(f'last_updated_{table}', str(current_datetime()), local)

    if not is_test_table:
        update_db_status_var(f'last_updated_{table}', str(current_datetime()), local)


def list_tables(con: Connection, schema: str = SCHEMA, filter_temp_refresh_tables=False) -> List[str]:
    """List tables
    :param filter_temp_refresh_tables: Filters out any temporary tables that are created during the refresh, e.g. ones
    that end w/ the suffix '_old'."""
    query = f"""
        SELECT relname
        FROM pg_stat_user_tables
        WHERE schemaname in ('{schema}') ORDER BY 1;"""
    result = run_sql(con, query)
    tables = [x[0] for x in result]
    if filter_temp_refresh_tables:
        tables = [x for x in tables if not x.endswith('_new') and not x.endswith('_old')]
    return tables


def get_ddl_statements(
    schema: str = SCHEMA, modules: List[str] = None, table_suffix='', index_suffix='', return_type=['flat', 'nested'][1]
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
      3. I think it's inserting a second ; at the end of the last statement of a given module"""
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
