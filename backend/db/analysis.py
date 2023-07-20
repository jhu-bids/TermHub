"""Utilities for database analysis, e.g. table counts

TODO's
  - add option to remove tables that don't exist in the latest state of a DB schema from the counts/deltas tables
  - manually remove some entries we don't need. perhaps write a function that deletes them by name/id. For id, we'd have
  to add that functionality as no id's currenlty exist. for names, these don't exist in the counts-run table. those are
  dynamically generated. could remove by timestamp, though, although that doesn't show in the counts/deltas tables, so
  that wouldn't work nicely either.
"""
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union
import dateutil.parser as dp
import pandas as pd
from jinja2 import Template
from pandas import Series


THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(THIS_DIR).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.config import DOCS_DIR
from backend.db.initialize import SCHEMA
from backend.db.utils import get_db_connection, insert_from_dict, list_tables, sql_query

COUNTS_OVER_TIME_OPTIONS = [
    'counts_table',
    'delta_table',
    # 'save_delta_viz'
]
DOCS_PATH = os.path.join(DOCS_DIR, 'backend', 'db', 'analysis.md')
DOCS_JINJA = """# DB row counts
## Deltas over time
{{ deltas_markdown_table }}

## Counts over time
{{ counts_markdown_table }}"""


# TODO: rename current_counts where from_cache = True to counts_history or something. because the datastructure is
#  different. either that, or have it re-use the from_cache code at the end if from_cache = False
#  - then, counts_over_time() & docs(): add cache param set to false, and change how they call current_counts()
def _current_counts(
    schema: str = SCHEMA, local=False, from_cache=False, return_as=['dict', 'df'][0], dt=datetime.now(),
    filter_temp_refresh_tables=False
) -> Union[pd.DataFrame, Dict]:
    """Gets current database counts"""
    if from_cache:
        with get_db_connection(schema='', local=local) as con:
            counts: List[Dict] = [dict(x) for x in sql_query(con, f'SELECT * from counts;', return_with_keys=True)]
            df = pd.DataFrame(counts)
            df = df[df['schema'] == schema]
            return df
    # Get tables
    with get_db_connection(schema=schema, local=local) as con:
        tables: List[str] = list_tables(con, filter_temp_refresh_tables=filter_temp_refresh_tables)
    with get_db_connection(schema='', local=local) as con:
        # Get previous counts
        timestamps: List[datetime] = [
            dp.parse(x[0]) for x in sql_query(con, f'SELECT DISTINCT timestamp from counts;', return_with_keys=False)]
        most_recent_timestamp: str = str(max(timestamps)) if timestamps else None
        prev_counts: List[Dict] = [dict(x) for x in sql_query(con, f'SELECT * from counts;', return_with_keys=True)]
        prev_counts_df = pd.DataFrame(prev_counts)
        # Get counts
        table_rows: Dict[str, Dict[str, Any]] = {}
        for table in tables:
            count: int = [x for x in sql_query(con, f'SELECT COUNT(*) from n3c.{table};', return_with_keys=False)][0][0]
            last_count = 0
            if most_recent_timestamp:
                last_count_fetch: Series = prev_counts_df[
                    (prev_counts_df['timestamp'] == most_recent_timestamp) &
                    (prev_counts_df['table'] == table)]['count']
                last_count_fetch2: List[int] = list(last_count_fetch.to_dict().values())
                last_count: int = int(last_count_fetch2[0]) if prev_counts and last_count_fetch2 else 0
            table_rows[table] = {
                'date': dt.strftime('%Y-%m-%d'),
                'timestamp': str(dt),
                'schema': schema,
                'table': table,
                'count': count,
                'delta': count - last_count,
            }
    return table_rows if return_as == 'dict' else pd.DataFrame(table_rows)


def counts_compare_schemas(
    compare_schema: str = 'most_recent_backup', schema: str = SCHEMA, local=False, verbose=True, use_cached_counts=False
) -> pd.DataFrame:
    """Checks counts of database tables for the current schema and its most recent backup.

    :param compare_schema: The schema to check against. e.g. ncurrent_counts3c_backup_20230322
    :param use_cached_counts: If True, will use whatever is in the `counts` table, though it is less likely that counts
    will exist for backups. Runs much faster though if using this option.
    """
    # Determine most recent schema if necessary
    if compare_schema == 'most_recent_backup':
        # 2nd % necessary for Python escaping
        query = """SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT LIKE 'pg_%%'
        AND schema_name <> 'information_schema';
        """
        with get_db_connection(schema='', local=local) as con:
            backup_schemas: List[str] = [x[0] for x in sql_query(con, query, return_with_keys=False) if x[0].startswith(f'{schema}_backup_')]
        dates: List[datetime] = [dp.parse(x.split('_')[2]) for x in backup_schemas]
        for schema_name, date in zip(backup_schemas, dates):
            if date == max(dates):
                compare_schema = schema_name

    # Get counts
    main: Dict = _current_counts(schema, from_cache=use_cached_counts, local=local)
    compare: Dict = _current_counts(compare_schema, from_cache=use_cached_counts, local=local)
    tables = set(main.keys()).union(set(compare.keys()))
    rows = []
    for table in tables:
        main_count = main[table]['count'] if table in main else 0
        compare_count = compare[table]['count'] if table in compare else 0
        rows.append({
            'table': table,
            'delta': main_count - compare_count,
            schema: main_count,
            compare_schema: compare_count,
        })
    df = pd.DataFrame(rows)

    if verbose:
        print(df)
    return df


def counts_update(note: str, schema: str = SCHEMA, local=False, filter_temp_refresh_tables=True):
    """Update 'counts' table with current row counts.
    :param note: For context around what was going on around when / why the counts are updated, e.g. after a backup or
    a data fetch from the enclave, or after editing a batch of concept sets.
    """
    dt = datetime.now()
    with get_db_connection(schema='', local=local) as con:
        # Save run metadata, e.g. a note about it
        insert_from_dict(con, 'public.counts_runs', {
            'timestamp': str(dt),
            'date': dt.strftime('%Y-%m-%d'),
            'schema': schema,
            'note': note,
        })
        # Save counts
        # noinspection PyCallingNonCallable pycharm_doesnt_undestand_its_returning_dict
        for d in _current_counts(
            from_cache=False, dt=dt, local=local, filter_temp_refresh_tables=filter_temp_refresh_tables).values():
            insert_from_dict(con, 'counts', d)


# TODO: support multiple schema
def counts_over_time(
    schema: str = SCHEMA, local=False, method=COUNTS_OVER_TIME_OPTIONS[0], _print=True,
    current_counts_df: pd.DataFrame = pd.DataFrame()
) -> pd.DataFrame:
    """Checks counts of database and store what the results look like in a database over time"""
    if method not in COUNTS_OVER_TIME_OPTIONS:
        raise ValueError(f'counts_over_time(): Invalid method {method}. Must be one of {COUNTS_OVER_TIME_OPTIONS}')
    current_counts_df = current_counts_df if len(current_counts_df) > 0 else _current_counts(
        schema, local, from_cache=True)

    # Pivot
    values = 'count' if method == 'counts_table' else 'delta'
    df = current_counts_df.pivot(index='table', columns='timestamp', values=values).fillna(0).astype(int)

    dateslist = [column[:10] for column in df.columns]
    dates = list(set(dateslist))

    finaldf = pd.DataFrame()
    for date in dates:
        count = dateslist.count(date)
        #creates a temporary table with the columns of only one date.
        datedf = df[df.columns[df.columns.str.startswith(date)]]
        datedf = datedf.sort_index(axis=1)
        datedf.loc[f'{values} over time, 1x/day'] = count
        if values == 'counts':
            #keeping only the most recent column from each day
            finaldf[date] = datedf.iloc[:, -1:]
        else:
            #keeping the sum of columns from each day
            row_sums = datedf.sum(axis=1)
            finaldf[date] = row_sums

    finaldf.columns = [col[:10] for col in finaldf.columns]
    finaldf = finaldf.sort_index(axis=1)
    finaldf = finaldf.iloc[:, ::-1]

    # Print / save
    if method == 'save_delta_viz':
        raise NotImplementedError('Option save_delta_viz for counts_over_time() not yet implemented.')
    elif _print:
        print(df.to_markdown(index=False))
    return finaldf

def counts_docs(use_cached_counts=True):
    """Runs --counts-over-time and --deltas-over-time and puts in documentation: docs/backend/db/analysis.md."""
    # Get data
    current_counts_df = _current_counts(from_cache=use_cached_counts)
    counts_df: pd.DataFrame = counts_over_time(method='counts_table', current_counts_df=current_counts_df, _print=False)
    deltas_df: pd.DataFrame = counts_over_time(method='delta_table', current_counts_df=current_counts_df, _print=False)
    # Write docs
    instantiated_str: str = Template(DOCS_JINJA).render(
        counts_markdown_table=counts_df.to_markdown(),
        deltas_markdown_table=deltas_df.to_markdown())
    with open(DOCS_PATH, 'w') as f:
        f.write(instantiated_str)
    # Notify
    # todo: notify param: need new method; Gmail doesn't work anymore. See: send_email() docstring
    # if notify:
    #     send_email(
    #         subject="TermHub DB counts docs updated",
    #         body="When/if pushed to develop branch, will appear here: "
    #              "https://github.com/jhu-bids/TermHub/blob/develop/docs/backend/db/analysis.md")


def cli():
    """Command line interface."""
    parser = ArgumentParser(prog='TermHub DB analysis utils.', description='Various analyses for DB.')
    parser.add_argument(
        '-c', '--counts-over-time', action='store_true',
        help="View counts row counts over time for the 'n3c' schema.")
    parser.add_argument(
        '-d', '--deltas-over-time', action='store_true',
        help="View row count deltas over time for the 'n3c' schema.")
    parser.add_argument(
        '-D', '--counts-docs', action='store_true',
        help="Runs --counts-over-time and --deltas-over-time and puts in documentation: docs/backend/db/analysis.md.")
    # --counts-update and its args
    parser.add_argument(
        '-u', '--counts-update', action='store_true',
        help="Update 'counts' table with current row counts for the 'n3c' schema.")
    parser.add_argument(
        '-n', '--note',
        help="Only used with `--counts-update`. Add a note to the 'counts-runs' table.")
    parser.add_argument(
        '-l', '--local', action='store_true', help="Use local database instead of production?")
    parser.add_argument(
        '-S', '--schema', default=SCHEMA,
        help="Only used with `--counts-update` and --counts-compare-schemas. Selects which schema's tables to count.")
    # --counts-compare-schemas and its args
    parser.add_argument(
        '-s', '--counts-compare-schemas', action='store_true',
        help="Checks counts of database tables for the current 'n3c' schema and its most recent backup.")
    parser.add_argument(
        '-C', '--schema-to-compare', default='most_recent_backup',
        help="Only used with `--counts-compare-schemas`. Selects which schema to compare to --schema (which by default "
             f"is '{SCHEMA}'). Default for schema to compare is whatever backup was the most recent, following naming "
             f"pattern of 'n3c_backup_YYYYMMDD'.")

    d: Dict = vars(parser.parse_args())
    local = d['local'] if d['local'] else False
    if d['counts_update']:
        note = (input("Please provide a note: ") if not d['note'] else d['note']).strip()
        if not note:
            raise ValueError('Must provide a note when using --counts-update.')
        counts_update(note, d['schema'])
    elif d['counts_compare_schemas']:
        counts_compare_schemas(d['schema_to_compare'], d['schema'], local=local)
    elif d['counts_over_time']:
        counts_over_time(method='counts_table', local=local)
    elif d['deltas_over_time']:
        counts_over_time(method='delta_table', local=local)
    elif d['counts_docs']:
        docs()
    else:
        print('Error: Choose 1 and only 1 option. Can see available options by running with --help', file=sys.stderr)


if __name__ == '__main__':
    cli()
