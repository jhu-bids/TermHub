"""Initialize database"""
import os
import re

import pandas as pd
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import text
# noinspection PyUnresolvedReferences
from psycopg2.errors import UndefinedTable

from backend.db.config import DATASETS_PATH, CONFIG, DDL_PATH, OBJECTS_PATH
from backend.db.utils import database_exists, run_sql, get_db_connection, DB, SCHEMA
from backend.utils import commify


def initialize():
    """Initialize set up of DB

    Resources
    - https://docs.sqlalchemy.org/en/20/core/engines.html
    - https://docs.sqlalchemy.org/en/20/dialects/mysql.html

    todo: (can do in ddl.sql): don't do anything if these tables exist & initialized
    """
    dataset_tables_to_load = [
        'code_sets',
        'concept',
        'concept_ancestor',
        'concept_relationship',
        'concept_relationship_subsumes_only',
        'concept_set_container',
        'concept_set_counts_clamped',
        'concept_set_members',
        'concept_set_version_item',
        'deidentified_term_usage_by_domain_clamped',
    ]
    object_tables_to_load = [
        'researcher',
        'OMOPConceptSet',          # to include RID
        'OMOPConceptSetContainer', # to include RID
        # 'OMOPConceptSetVersionItem', only need this if we want the RID, but maybe don't need it
    ]
    # TODO: alter these columns as indicated:
    # datetime_cols = [
    #     ('code_sets', 'created_at'),
    #     ()]
    # date_cols = [
    #     ('concept', 'valid_end_date'),
    #     ('concept', 'valid_start_date'),
    #     ('concept_relationship', 'valid_end_date'),
    #     ('concept_relationship', 'valid_start_date')]

    with get_db_connection() as con:
        if CONFIG["server"] != 'postgresql':  # postgres doesn't have create database if not exists
            run_sql(con, 'CREATE DATABASE IF NOT EXISTS ' + DB)
            run_sql(con, f'USE {DB}')
        else:
            if not database_exists(con, DB):
                con.connection.connection.set_isolation_level(0)
                run_sql(con, 'CREATE DATABASE ' + DB)
                con.connection.connection.set_isolation_level(1)

            # create schema isn't working, not sure why -- I had to create it manually
            # run_sql(con, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
            # run_sql(con, f'SET search_path TO {SCHEMA}, public')
            # doesn't work:
            # run_sql(con, f'SET search_path TO {SCHEMA}')
            # being handled by get_db_connection

        for table in dataset_tables_to_load:
            load_csv(con, table, replace_rule='do not replace')
        for table in object_tables_to_load:
            # use table.lower() because postgres won't recognize names with caps in them unless they
            #   are "quoted". should probably do this with colnames also, but just using quotes in ddl
            load_csv(con, table.lower(), table_type='object', replace_rule='do not replace')

        # TODO: run ddl
        #  a. use this delimiter thing. how delimit? ;\n\n? #--?
        #  b. sql alchemy: run sql string
        #  c. subprocess: psql termhub -i path/to/file
        print('INFO: Creating derived tables (e.g. `all_csets`) and indexes.')
        with open(DDL_PATH, 'r') as file:
            contents: str = file.read()
        run_sql(con, contents)
        # commands: List[str] = [x + ';' for x in contents.split(';\n\n')]
        # for command in commands:
        #     try:
        #         run_sql(con, command)
        #     except (ProgrammingError, OperationalError):
        #         raise RuntimeError(f'Got an error executing the following statement:\n{command}')

    return


def load_csv(
    con: Connection, table: str, table_type: str = ['dataset', 'object'][0], replace_rule='replace if diff row count'):
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
            print(f'INFO: {SCHEMA}.{table} does not not exist; will create it')
        else:
            raise err

    if replace_rule == 'do not replace' and existing_rows > 0:
        print(f'INFO: {SCHEMA}.{table} exists with {commify(existing_rows)} rows; leaving it')
        return

    # Load table
    path = os.path.join(DATASETS_PATH, f'{table}.csv') if table_type == 'dataset' \
        else os.path.join(OBJECTS_PATH, table, 'latest.csv')
    df = pd.read_csv(path)

    if replace_rule == 'replace if diff row count' and existing_rows == len(df):
        print(f'INFO: {SCHEMA}.{table} exists with same number of rows {existing_rows}; leaving it')
        return

    print(f'INFO: \nloading {SCHEMA}.{table} into {CONFIG["server"]}:{DB}')
    # Clear data if exists
    try:
        con.execute(text(f'TRUNCATE {SCHEMA}.{table}'))
    except ProgrammingError:
        pass

    # Load
    # `schema='termhub_n3c'`: Passed so Joe doesn't get OperationalError('(pymysql.err.OperationalError) (1050,
    #  "Table \'code_sets\' already exists")')
    #  https://stackoverflow.com/questions/69906698/pandas-to-sql-gives-table-already-exists-error-with-if-exists-append
    kwargs = {'if_exists': 'append', 'index': False, 'schema': SCHEMA}
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


if __name__ == '__main__':
    initialize()
