"""Initialize database"""
from typing import List
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
# from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
from pymysql.err import DataError
import re
from backend.db.mysql_utils import run_sql, get_mysql_connection
from backend.db.config import CONFIG


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
    with get_mysql_connection() as con:

        # postgres doesn't have create database if not exists
        # run_sql(con, 'CREATE DATABASE IF NOT EXISTS termhub_n3c')
        # run_sql(con, 'USE termhub_n3c')

        for table in tables_to_load:
            print(f'loading {table} into {CONFIG["server"]}:{CONFIG["db"]}')
            load_csv(con, table)

        datetime_cols = [('code_sets', 'created_at'),
                         ()]
        date_cols = [('concept', 'valid_end_date'),
                     ('concept', 'valid_start_date'),
                     ('concept_relationship', 'valid_end_date'),
                     ('concept_relationship', 'valid_start_date')
                     ]
        # TODO: alter columns above as indicated

        # with open(DDL_PATH, 'r') as file:
        #     contents: str = file.read()
        # commands: List[str] = [x + ';' for x in contents.split(';\n')]
        # for command in commands:
        # Insert data
        # except (ProgrammingError, OperationalError):
        #     raise RuntimeError(f'Got an error executing the following statement:\n{command}')

    return

def load_csv(con, table, replace_if_exists=True):
    df = pd.read_csv(f'~/git-repos/TermHub/termhub-csets/datasets/prepped_files/{table}.csv')
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    # df.to_sql(name, con, schema=None, if_exists='fail', index=True, index_label=None, chunksize=None, dtype=None, method=None)
    # todo: fix "data too long" / data type issues:
    #  @Siggie: how to iteratively fix: (i) drop table, (ii) recreate table, (iii) rerun this script
    #  sqlalchemy.exc.DataError: (pymysql.err.DataError) (1406, "Data too long for column 'atlas_json_resource_url' at row 274")
    #  @jflack4: "data too long" is fixed. there are other changes we probably want to make with these pandas-created
    #            tables. Like datetimes.... doing some of this above now
    if not replace_if_exists:
        # TODO: make this work:
        # query:  show tables where Tables_in_termhub_n3c = {table}
        # if query not returns empty:
        #   return
        pass
    try:
        con.execute(text(f'TRUNCATE {table}'))
    except ProgrammingError as err:
        pass
    try:
        df.to_sql(table, con, if_exists='append', index=False)
    except Exception as err:
        # if data too long error, change column to longtext and try again
        m = re.match("Data too long for column '(.*)'.*", err.orig.args[1])
        if (m):
            run_sql(con, f'ALTER TABLE {table} MODIFY {m[1]} LONGTEXT')
            load_csv(con, table)
        else:
            raise err
    # except Exception as err:
    #     print(err)

# pymysql.err.OperationalError: (1290, 'The MySQL server is running with the --secure-file-priv option so it cannot execute this statement')


if __name__ == '__main__':
    # May not ever need to connect directly to 'termhub' db, at least not in initialization
    # try:
    #     initialize(DB_URL)
    # except OperationalError:
    #     initialize(BRAND_NEW_DB_URL)
    initialize()
