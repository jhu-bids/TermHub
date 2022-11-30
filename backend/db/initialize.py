"""Initialize database"""
import os
import re

import pandas as pd
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import text

from backend.db.config import DATASETS_PATH, CONFIG
from backend.db.utils import run_sql, get_db_connection


def initialize():
    """Initialize set up of DB

    Resources
    - https://docs.sqlalchemy.org/en/20/core/engines.html
    - https://docs.sqlalchemy.org/en/20/dialects/mysql.html

    todo: (can do in ddl.sql): don't do anything if these tables exist & initialized
    """
    tables_to_load = [
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
    with get_db_connection(new_db=True) as con:

        # postgres doesn't have create database if not exists
        # run_sql(con, 'CREATE DATABASE IF NOT EXISTS termhub_n3c')
        # run_sql(con, 'USE termhub_n3c')

        for table in tables_to_load:
            print(f'loading {table} into {CONFIG["server"]}:{CONFIG["db"]}')
            load_csv(con, table)

        datetime_cols = [
            ('code_sets', 'created_at'),
            ()]
        date_cols = [
            ('concept', 'valid_end_date'),
            ('concept', 'valid_start_date'),
            ('concept_relationship', 'valid_end_date'),
            ('concept_relationship', 'valid_start_date')]
        # TODO: alter columns above as indicated

        # with open(DDL_PATH, 'r') as file:
        #     contents: str = file.read()
        # commands: List[str] = [x + ';' for x in contents.split(';\n')]
        # for command in commands:
        # Insert data
        # except (ProgrammingError, OperationalError):
        #     raise RuntimeError(f'Got an error executing the following statement:\n{command}')

    return


def load_csv(con: Connection, table: str, replace_if_exists=True):
    """Load CSV into table

    - Uses: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    """
    df = pd.read_csv(os.path.join(DATASETS_PATH, f'{table}.csv'))
    if not replace_if_exists:
        # TODO: make this work:
        # query:  show tables where Tables_in_termhub_n3c = {table}
        # if query not returns empty:
        #   return
        pass
    try:
        con.execute(text(f'TRUNCATE {table}'))
    except ProgrammingError:
        pass
    # `schema='termhub_n3c'`: Passed so Joe doesn't get OperationalError('(pymysql.err.OperationalError) (1050,
    #  "Table \'code_sets\' already exists")')
    #  https://stackoverflow.com/questions/69906698/pandas-to-sql-gives-table-already-exists-error-with-if-exists-append
    try:
        df.to_sql(table, con, if_exists='append', schema='termhub_n3c', index=False)
    except Exception as err:
        # if data too long error, change column to longtext and try again
        # noinspection PyUnresolvedReferences
        m = re.match("Data too long for column '(.*)'.*", err.orig.args[1])
        if m:
            run_sql(con, f'ALTER TABLE {table} MODIFY {m[1]} LONGTEXT')
            load_csv(con, table)
        else:
            raise err
    # except Exception as err:
    #     print(err)


if __name__ == '__main__':
    initialize()
