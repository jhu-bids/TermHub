"""Refresh vocabulary and counts tables

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
from typing import List

from dateutil import parser as dp


DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.utils import SCHEMA, check_db_status_var, get_db_connection, get_ddl_statements, load_csv, \
    refresh_any_dependent_tables, \
    run_sql
from enclave_wrangler.config import DATASET_GROUPS_CONFIG
from enclave_wrangler.datasets import download_datasets, get_last_update_of_dataset


def refresh_voc_and_counts(skip_downloads: bool = False, schema=SCHEMA):
    """Refresh vocabulary and counts tables."""
    print('Refreshing vocabulary and counts tables.')
    for group_name, config in DATASET_GROUPS_CONFIG.items():
        print(f'\nRefreshing {group_name} tables...')
        # Check if tables are already up to date
        last_updated_us: str = check_db_status_var(config['last_updated_termhub_var'])
        last_updated_them: str = get_last_update_of_dataset(config['last_updated_enclave_representative_table'])
        if last_updated_us and last_updated_them and dp.parse(last_updated_us) > dp.parse(last_updated_them):
            print('Tables already up to date. Nothing to be done.')
            continue
        # Download datasets
        if not skip_downloads:
            print('Downloading datasets')
            download_datasets(single_group=group_name)
        # Load data
        print('Loading downloaded datasets into DB tables')
        with get_db_connection(schema=schema) as con:
            for table in config['tables']:
                print(f' - loading {table}...')
                t0 = datetime.now()
                load_csv(con, table, replace_rule='do not replace', schema=SCHEMA, optional_suffix='_new')
                run_sql(con, f'ALTER TABLE IF EXISTS {schema}.{table} RENAME TO {table}_old;')
                run_sql(con, f'ALTER TABLE {schema}.{table}_new RENAME TO {table};')
                run_sql(con, f'DROP TABLE IF EXISTS {schema}.{table}_old;')
                t1 = datetime.now()
                print(f'   done in {(t1 - t0).seconds} seconds')
                # todo: set variable for 'last updated' for each table (look at load())
                #  - consider: check if table already updated sooner than last_updated_them. if so, skip. and add a param to CLI for this
            print('Creating indexes')
            statements: List[str] = get_ddl_statements(schema, ['indexes'], 'flat')
            for statement in statements:
                run_sql(con, statement)
            # print('Recreating derived tables')  # printed w/in refresh_derived_tables()
            refresh_any_dependent_tables(con, config['tables'])

    print('Done')


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='Refresh vocabulary and counts tables.')
    parser.add_argument(
        '-s', '--skip-downloads', action='store_true',
        help='Use if you have already downloaded updated files.')
    refresh_voc_and_counts(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
