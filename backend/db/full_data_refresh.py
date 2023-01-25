"""
Fully refresh the database with the latest data from the enclave API.
  here's what the run file is doing, i think, for datasets:
    ./venv/bin/python enclave_wrangler/datasets.py -f -o termhub-csets/datasets/downloads
"""
import json
import os
import sys
from argparse import ArgumentParser

import dateutil.parser as dp
from datetime import datetime, timezone

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.config import CONFIG, DB_DIR
from backend.db.load import load
from backend.db.utils import current_datetime, get_db_connection, run_sql
from enclave_wrangler.datasets import download_favorite_datasets
from enclave_wrangler.objects_api import download_favorite_objects


# TODO: Refactor: create a table 'manage' and store the last_refresh_datetime? If less than 1 day, don't do again
def db_outdated(threshold_hours=24) -> bool:
    """Check if the database is outdated"""
    last_updated = None
    # noinspection PyBroadException
    try:
        with open(os.path.join(DB_DIR, 'manage.json'), 'r') as file:
            data = json.loads(file.read())
            last_updated = dp.parse(data['last_updated'])
    except Exception:
        pass
    hours_since_update = (dp.parse(current_datetime()) - last_updated).total_seconds() / 60 / 60 \
        if last_updated else 25
    return not last_updated or hours_since_update >= threshold_hours


def refresh_db(
    datasets_csets=False, datasets_vocab=False, objects=False, force_if_exists=False, schema: str = CONFIG['schema']
):
    """Refresh the database"""
    schema_new_temp = schema + '_' + datetime.now().strftime('%Y%m%d')
    schema_old_backup = schema + '_before_' + datetime.now().strftime('%Y%m%d')
    outdated: bool = db_outdated()

    # todo: also add last updated functionality on a more granular basis based on which of these 3?
    if outdated and datasets_csets:
        download_favorite_datasets(force_if_exists=force_if_exists, single_group='cset')
    if outdated and objects:
        download_favorite_objects(force_if_exists=force_if_exists)
    if outdated and datasets_vocab:
        download_favorite_datasets(force_if_exists=force_if_exists, single_group='vocab')
    if not outdated:
        print('INFO: Skipping download of datasets and objects as they are up to date.')

    with get_db_connection() as con:
        run_sql(con, f'CREATE SCHEMA IF NOT EXISTS {schema_new_temp};')
    with get_db_connection(schema=schema_new_temp) as con:
        # TODO: within load() func below comment out seed() troubleshoot indexes_and_derived_tables()
        # TODO: add 'last updated' for each table in (i) seed(), and (ii) indexes_and_derived_tables()s
        load(schema=schema_new_temp, clobber=True)
        run_sql(con, f'ALTER SCHEMA n3c RENAME TO {schema_old_backup};')
        run_sql(con, f'ALTER SCHEMA {schema_new_temp} RENAME TO n3c;')
        # TODO: refactor (see db_outdated()):
        with open(os.path.join(DB_DIR, 'manage.json'), 'w') as file:
            json.dump({'last_updated': datetime.now(timezone.utc).isoformat()}, file)
        print('INFO: Database refresh complete.')


def cli():
    """Command line interface"""
    parser = ArgumentParser(description='Refreshes the TermHub database w/ newest updates from the Enclave.')
    parser.add_argument('-o', '--objects', action='store_true', default=False, help='Download objects.')
    parser.add_argument(
        '-c', '--datasets-csets', action='store_true', default=False, help='Download datasets from the "cset" group.')
    parser.add_argument(
        '-v', '--datasets-vocab', action='store_true', default=False, help='Download datasets from the "vocab" group.')
    parser.add_argument(
        '-f', '--force-if-exists', action='store_true', default=False,
        help='If the dataset/object already exists as a local file, force a re-download.')
    refresh_db(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
