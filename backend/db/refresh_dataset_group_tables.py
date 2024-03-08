"""Refresh tables by dataset group (e.g. vocabulary and counts)

todo's
  1. minor: Increse performance: updates > remakeing tables
  Similar to what DB refresh: performance: Derived tables: Inserts > remakes #448 intends w/ the derived tables, perhaps
  we want to update tables rather than remake them? E.g. (i) deletes: when we fetch new datasets, remove any rows from
  the corresponding DB table if they don't exist in the newly downloaded dataset (indicating that they're delated, and
  (ii) creates: add any new rows in the new dataset if they don't exist in the corresponding table. And then there's
  also (iii) updates: is it possible for rows/records to be updated?
  2. Duplicative logic: runs same stuff for (i) voc, (ii) counts. can refactor to be more DRY?
  3. CLI: add --use-local-db one day perhaps
"""
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

from dateutil import parser as dp


DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.analysis import counts_docs, counts_update
from backend.db.utils import SCHEMA, check_db_status_var, current_datetime, get_db_connection, get_ddl_statements, \
    load_csv, refresh_derived_tables, reset_temp_refresh_tables, run_sql, update_db_status_var
from enclave_wrangler.config import DATASET_GROUPS_CONFIG
from enclave_wrangler.datasets import download_datasets, get_datetime_dataset_last_updated


def load_dataset_group(dataset_group_name: str, schema: str = SCHEMA, alternate_dataset_dir: Union[Path, str] = None):
    """Load data

    :param alternate_dataset_dir: Designed mainly for automated tests to load input files to test schema."""
    config: Dict = DATASET_GROUPS_CONFIG[dataset_group_name]
    # noinspection PyBroadException
    try:
        with get_db_connection(schema=schema) as con:
            for table in config['tables']:  # tables themselves (non-derived)
                print(f' - loading {table}...')
                t0 = datetime.now()
                load_csv(
                    con, table, replace_rule='do not replace', schema=schema, optional_suffix='_new',
                    path_override=Path(alternate_dataset_dir) / f'{table}.csv' if alternate_dataset_dir else None,
                    is_test_table=bool(alternate_dataset_dir))
                run_sql(con, f'ALTER TABLE IF EXISTS {schema}.{table} RENAME TO {table}_old;')
                run_sql(con, f'ALTER TABLE {schema}.{table}_new RENAME TO {table};')

                # Primary keys
                # - setting all of them; quick operation, and only creates if not exist
                statements: List[str] = get_ddl_statements(schema, ['primary_keys'], return_type='flat')
                for statement in statements:
                    run_sql(con, statement)

                # Indexes
                statements: List[str] = get_ddl_statements(schema, ['indexes'], return_type='flat')
                statements = [x for x in statements if f'{schema}.{table}(' in x]  # filter for this table
                for statement in statements:
                    run_sql(con, statement)

                t1 = datetime.now()
                # todo: set variable for 'last updated' for each table (look at load())
                #  - consider: check if table already updated sooner than last_updated_them. if so, skip. and add a param to CLI for this
                print(f'   done in {(t1 - t0).seconds} seconds')

            print('Recreating derived tables')  # derived tables
            refresh_derived_tables(con, config['tables'], schema)

            print('Deleting old, temporarily backed up versions of tables')
            for table in config['tables']:
                run_sql(con, f'DROP TABLE IF EXISTS {schema}.{table}_old;')
    except Exception as err:
        reset_temp_refresh_tables(schema)
        raise err


def refresh_dataset_group_tables(
    dataset_group: List[str], skip_downloads: bool = False, download_only: bool = False, schema=SCHEMA
):
    """Refresh tables by dataset group (e.g. vocabulary and counts)"""
    print(f'Refreshing tables for the following dataset groups: {",".join(dataset_group)}')
    selected_configs = {k: v for k, v in DATASET_GROUPS_CONFIG.items() if k in dataset_group}
    for group_name, config in selected_configs.items():
        print(f'\nRefreshing {group_name} tables...')
        # Check if tables are already up-to-date
        last_updated_us: str = check_db_status_var(config['last_updated_termhub_var'])
        last_updated_them: str = get_datetime_dataset_last_updated(config['last_updated_enclave_representative_table'])
        if last_updated_us and last_updated_them and dp.parse(last_updated_us) > dp.parse(last_updated_them):
            print('Tables already up to date. Nothing to be done.')
            continue

        # Download datasets
        if not skip_downloads:
            print('Downloading datasets')
            download_datasets(single_group=group_name)

        # Load data
        if not download_only:
            print('Loading downloaded datasets into DB tables')
            load_dataset_group(group_name, schema)

            # Mark complete
            update_db_status_var(config['last_updated_termhub_var'], current_datetime())

            # DB Counts
            print('Updating database counts. This could take a while...')
            counts_update(f'DB refresh: {",".join(dataset_group)}', schema)
    print('Done')


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='Refresh tables by dataset group (e.g. vocabulary and counts)')
    parser.add_argument(
        '-d', '--dataset-group', nargs='+', choices=list(DATASET_GROUPS_CONFIG.keys()),
        default=list(DATASET_GROUPS_CONFIG.keys()),
        help='Names of dataset/table groups to refresh.')
    parser.add_argument(
        '-s', '--skip-downloads', action='store_true',
        help='Use if you have already downloaded updated files.')
    parser.add_argument(
        '-D', '--download-only', action='store_true',
        help='Use if you want to download the dataset files and upload them later.')
    refresh_dataset_group_tables(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
