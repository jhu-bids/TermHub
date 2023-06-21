"""Utils for database usage

todo's
  1. Some functions could be improved using `sql_query()` `params` arg to be less prone to sql injection.
"""
import json
import os
import pytz
import dateutil.parser as dp
from datetime import datetime, timezone
from glob import glob

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

from backend.db.config import CONFIG, DATASETS_PATH, DDL_JINJA_PATH_PATTERN, OBJECTS_PATH, get_pg_connect_url
from backend.utils import commify
from enclave_wrangler.models import pkey

DEBUG = False
DB = CONFIG["db"]
SCHEMA = CONFIG["schema"]


# todo: move this somewhere else, possibly load.py or db_refresh.py
# todo: what to do if this process fails? any way to roll back? should we?
def refresh_termhub_core_cset_derived_tables(con: Connection, schema: str):
    """Refresh TermHub core cset derived tables

    This can also work to initially create the tables if they don't already exist."""
    temp_table_suffix = '_new'
    # TODO: update when I have DDL for public.csets_to_ignore
    ddl_modules = [
        'cset_members_items',
        'concept_ids_by_codeset_id',
        'codeset_ids_by_concept_id',
        'members_items_summary',
        'cset_members_items_plus',
        'codeset_counts',
        'all_csets',
        'csets_to_ignore',
    ]
    views = [
        'cset_members_items_plus',
        'csets_to_ignore',
    ]
    # Create new tables and backup old ones
    t0 = datetime.now()
    for module in ddl_modules:
        print(f'Running SQL to recreate derived table: {module}...')
        statements: List[str] = get_ddl_statements(schema, [module], temp_table_suffix)
        for statement in statements:
            run_sql(con, statement)
        # todo: warn if counts in _new table not >= _old table (if it exists)?
        run_sql(con, f'ALTER TABLE IF EXISTS {schema}.{module} RENAME TO {module}_old;')
        run_sql(con, f'ALTER TABLE {schema}.{module}{temp_table_suffix} RENAME TO {module};')
    # - Delete old tables. Because of view dependencies, order & commands are different
    t1 = datetime.now()
    print(f'Derived tables all created in {(t1 - t0).seconds} seconds. Removing older, temporarily backed up copies...')
    for view in views:
        ddl_modules.remove(view)
        run_sql(con, f'DROP VIEW IF EXISTS {schema}.{view}_old;')
    for module in ddl_modules:
        run_sql(con, f'DROP TABLE IF EXISTS {schema}.{module}_old;')


def get_db_connection(isolation_level='AUTOCOMMIT', schema: str = SCHEMA, local=False):
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


def update_db_status_var(key: str, val: str):
    """Update the `manage` table with information for a given variable, e.g. when a table was last updated
    todo: change to a 1-liner UPDATE statement"""
    with get_db_connection(schema='') as con2:
        run_sql(con2, f"DELETE FROM public.manage WHERE key = '{key}';")
        sql_str = f"INSERT INTO public.manage (key, value) VALUES (:key, :val);"
        run_sql(con2, sql_str, {'key': key, 'val': val})


def database_exists(con: Connection, db_name: str) -> bool:
    """Check if database exists"""
    result = \
        run_sql(con, f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{db_name}';").fetchall()
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
    keys_str = ' AND '.join([f'{key} = (:{key}_id)' for key in keys])
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
    results: List[RowMapping] = sql_query(
        con, f"SELECT * FROM {table} WHERE {' AND '.join([f'{k} {sql_in(v, True)}' for k, v in key_vals.items()])};",
        return_with_keys=True)
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
    res = sql_query(con, query, return_with_keys=False)
    if print_dump:
        print(pd.DataFrame(res))
        # print('\n'.join([', '.join(r) for r in res])) ugly
        # print(pdump(res)) doesn't work
    return res


def load_csv(
    con: Connection, table: str, table_type: str = ['dataset', 'object'][0], replace_rule='replace if diff row count',
    schema: str = SCHEMA, is_test_table=False
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
        r = con.execute(f'select count(*) from {schema}.{table}')
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
    path = os.path.join(DATASETS_PATH, f'{table}.csv') if table_type == 'dataset' \
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
    df.to_sql(table, con, **kwargs)

    update_db_status_var(f'last_updated_{table}', str(current_datetime()))

    if not is_test_table:
        update_db_status_var(f'last_updated_{table}', str(current_datetime()))


def list_tables(con: Connection, schema: str = SCHEMA) -> List[str]:
    """List tables"""
    query = f"""
        SELECT relname
        FROM pg_stat_user_tables
        WHERE schemaname in ('{schema}') ORDER BY 1;"""
    result = run_sql(con, query)
    return [x[0] for x in result]


def get_ddl_statements(schema: str = SCHEMA, modules: List[str] = None, table_suffix='') -> List[str]:
    """From local SQL DDL Jinja2 templates, pa rse and get a list of SQL statements to run.

    :param: modules: DDL files follow the naming schema `ddl-ORDER_NUMBER-MODULE_NAME.jinja.sql`. If `modules` is
    provided, will only return statements for those modules. If not provided, will return all statements.
    :param table_suffix: Used by DB refresh. This is used by a subset of the DDL modules. The use case here is that in
    order to refresh the DB, rather than doing inserts on existing derived tables, we re-run the DDL to create new
    tables with a suffix, then drop the original and rename the one we just created to remove the suffix.

    todo's
      1. For each table: don't do anything if these tables exist & initialized
      2. Add alters to fix data types (although, should really move this stuff to dtypes settings when creating
      dataframe that loads data into db."""
    paths: List[str] = glob(DDL_JINJA_PATH_PATTERN)
    if modules:
        paths = [p for p in paths if any([m == os.path.basename(p).split('-')[2].split('.')[0] for m in modules])]
    paths = sorted(paths, key=lambda x: int(os.path.basename(x).split('-')[1]))
    statements: List[str] = []
    for path in paths:
        with open(path, 'r') as file:
            template_str = file.read()
        ddl_text = Template(template_str).render(schema=schema + '.', optional_suffix=table_suffix)
        # Each DDL file should have 1 or more statements separated by an empty line (two line breaks).
        statements.extend([x + ';' for x in ddl_text.split(';\n\n')])
    return statements
