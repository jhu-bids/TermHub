"""Utilities for database analysis, e.g. table counts"""
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Dict, List
import dateutil.parser as dp
import pandas as pd

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(THIS_DIR).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.initialize import SCHEMA
from backend.db.utils import get_db_connection, insert_from_dict, list_tables, run_sql

COUNTS_OVER_TIME_OPTIONS = ['print_counts_table', 'print_delta_table', 'save_delta_viz']


# TODO: automatically compare to most recent backup. currently fixed to a specific schema
def counts_compare_schemas(
    compare_schema: str = 'n3c_backup_20230414', schema: str = SCHEMA, local=False, fast_approx_method=False,
    verbose=True
) -> List[tuple]:
    """Checks counts of database tables for the current schema and its most recent backup.

    :param compare_schema: The schema to check against. e.g. n3c_backup_20230322
    """
    # TODO: automatically determine latest backup name rather than param
    # TODO: format this to return something better. Right now looks like:
    #  [('code_sets', 'test2_n3c', 1), ('code_sets', 'test_n3c', 1), ('concept_set_container', 'test2_n3c', 1),
    #  ('concept_set_container', 'test_n3c', 1), ('concept_set_members', 'test2_n3c', 1), ('concept_set_members',
    #  'test_n3c', 1), ('concept_set_version_item', 'test2_n3c', 1), ('concept_set_version_item', 'test_n3c', 1)]
    # todo: pass params (not working right now for some reason) to run_sql() instead of string interpolating, e.g.:
    #  WHERE schemaname in (:schema_names)...
    # TODO: get this from the db instead of hardcoding
    query = f"""
    WITH tbl AS  (SELECT table_schema, TABLE_NAME
    FROM information_schema.tables
    WHERE TABLE_NAME not like 'pg_%' AND table_schema in ('{schema}', '{compare_schema}')) 
    SELECT table_schema, TABLE_NAME, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, TABLE_NAME), FALSE, TRUE, '')))[1]::text::int AS rows_n
    FROM tbl
    ORDER BY rows_n DESC
    """
    if fast_approx_method:
        query = f"""
        SELECT relname,schemaname,n_live_tup
        FROM pg_stat_user_tables
        WHERE schemaname in ('{schema}', '{compare_schema}')ORDER BY 1, 2, 3;"""

    with get_db_connection(schema=schema, local=local) as con:
        result = run_sql(con, query)
        result = [x for x in result]

    if verbose:
        pprint(result)
    return result


def counts_update(schema: str = SCHEMA, local=False):
    """Update 'counts' table with current row counts."""
    dt = datetime.now()
    with get_db_connection(schema=schema, local=local) as con:
        tables: List[str] = list_tables(con)
    with get_db_connection(schema='', local=local) as con:
        timestamps: List[datetime] = [dp.parse(x[0]) for x in run_sql(con, f'SELECT DISTINCT timestamp from counts;')]
        most_recent_timestamp: str = str(max(timestamps))
        prev_counts: List[Dict] = [dict(x) for x in run_sql(con, f'SELECT * from counts;')]
        prev_counts_df = pd.DataFrame(prev_counts)
        for table in tables:
            count: int = [x for x in run_sql(con, f'SELECT COUNT(*) from n3c.{table};')][0][0]
            last_count = int(prev_counts_df[
                (prev_counts_df['timestamp'] == most_recent_timestamp) &
                (prev_counts_df['table'] == table)]['count']) if prev_counts else count
            insert_from_dict(con, 'counts', {
                'date': dt.strftime('%Y-%m-%d'),
                'timestamp': str(dt),
                'schema': schema,
                'table': table,
                'count': count,
                'delta': count - last_count,
            })


def counts_over_time(
    schema: str = SCHEMA, local=False, method=COUNTS_OVER_TIME_OPTIONS[0]
):
    """Checks counts of database and store what the results look like in a database over time"""
    with get_db_connection(schema='', local=local) as con:
        counts: List[Dict] = [dict(x) for x in run_sql(con, f'SELECT * from counts;')]
        counts_df = pd.DataFrame(counts)
        counts_df = counts_df[counts_df['schema'] == schema]
        values = 'count' if method == 'print_counts_table' else 'delta'
        df = counts_df.pivot(index='table', columns='timestamp', values=values)
        if method == 'save_delta_viz':  # TODO
            pass
        else:
            print(df)


def cli():
    """Command line interface."""
    parser = ArgumentParser(prog='TermHub DB analysis utils.', description='Various analyses for DB.')
    parser.add_argument(
        '-c', '--counts-compare-schemas', action='store_true',
        help="Checks counts of database tables for the current 'n3c' schema and its most recent backup.")
    parser.add_argument(
        '-u', '--counts-update', action='store_true',
        help="Update 'counts' table with current row counts for the 'n3c' schema.")
    parser.add_argument(
        '-t', '--counts-over-time', choices=COUNTS_OVER_TIME_OPTIONS,
        help="View counts row counts over time for the 'n3c' schema.")

    d: Dict = vars(parser.parse_args())
    if d['counts_compare_schemas']:
        counts_compare_schemas()
    if d['counts_update']:
        counts_update()
    if d['counts_over_time']:
        counts_over_time(method=d['counts_over_time'])


if __name__ == '__main__':
    cli()
