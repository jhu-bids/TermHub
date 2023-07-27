"""Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new,
resulting in initial fetch of concept set members being 0."""
import os
import sys
from argparse import ArgumentParser

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.utils import SCHEMA, fetch_status_set_success, get_db_connection, insert_from_dicts, \
    refresh_termhub_core_cset_derived_tables, \
    select_failed_fetches

DESC = 'Resolve any failures resulting from fetching data from the Enclave\'s objects API.'

def resolve_fetch_failures_0_members(version_id: int = None, use_local_db=False):
    """Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new
    resulting in initial fetch of concept set members being 0.
    :param version_id: Optional concept set version ID to resolve. If not provided, will check database for flagged
    failures."""
    print('Resolving fetch failures: new concept set / 0 members')
    print('id:')
    print(version_id)
    if version_id:
        print(f'Fetching version ID: {version_id}')
        with get_db_connection(local=use_local_db) as con:
            pass
            # refresh_termhub_core_cset_derived_tables(con, SCHEMA)


# todo: Ideally allow for output_dir for testing purposes etc, but datasets.py currently supports only 1 of 2 outdirs
#  needed. See 'todo' above its cli() func.
def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='Resolve fetch failures.', description=DESC)
    parser.add_argument(
        '-l', '--use-local-db', action='store_true', default=False, required=False,
        help='Use local database instead of server.')
    parser.add_argument(
        '-v', '--version-id', required=False,
        help='Optional concept set version ID to resolve. If not provided, will check database for flagged failures.')
    resolve_fetch_failures_0_members(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
