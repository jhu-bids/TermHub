"""Resolve failures due to too many expression items or members when fetching data from the Enclave's objects API."""
import os
import sys
from argparse import ArgumentParser
from typing import Dict, List, Set

import pandas as pd

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.utils import SCHEMA, fetch_status_set_success, get_db_connection, insert_from_dicts, \
    refresh_termhub_core_cset_derived_tables, \
    select_failed_fetches
from enclave_wrangler.datasets import CSV_TRANSFORM_DIR, download_datasets
from enclave_wrangler.utils import was_file_modified_within_threshold

DESC = "Resolve failures due to too many expression items or members when fetching data from the Enclave's objects API."

def resolve_fetch_failures_excess_items(use_local_db=False, cached_dataset_threshold_hours=0):
    """Resolve failures due to too many expression items or members when fetching data from the Enclave's objects API.
    cached_dataset_threshold_hours: Threshold, in hours, until cached datasets considered invalid and need to be
    re-downloaded.
    """
    print('Resolve failures due to too many expression items or members when fetching data from the Enclave\'s '
          'objects API by using datasets API instead.')
    # Vars
    datasets = ['concept_set_version_item', 'concept_set_members']
    failure_dataset_map = {
        'fail-excessive-items': 'concept_set_version_item',
        'fail-excessive-members': 'concept_set_members',
    }
    dataset_path_map: Dict[str, str] = {ds: os.path.join(CSV_TRANSFORM_DIR, f'{ds}.csv') for ds in datasets}

    # Determine if any failures & what needs to be done
    failures: List[Dict] = select_failed_fetches(use_local_db)
    if not failures:
        return

    datasets_needed: Set[str] = set()
    failures_by_dataset: Dict[str, List[Dict]] = {}
    for failure in failures:
        dataset: str = failure_dataset_map[failure['status_initially']]
        datasets_needed.add(dataset)
        if not dataset in failures_by_dataset:
            failures_by_dataset[dataset] = []
        failures_by_dataset[dataset].append(failure)

    # Download datasets
    # - Determine if cache OK
    for dataset in list(datasets_needed):
        path = dataset_path_map[dataset]
        if cached_dataset_threshold_hours and was_file_modified_within_threshold(path, cached_dataset_threshold_hours):
            datasets_needed.remove(dataset)
    # - Download
    if datasets_needed:
        print(f'Downloading datasets: {", ".join(datasets_needed)}')
        download_datasets(specific=list(datasets_needed))
    else:
        print('Skipping dataset downloads. Cached datasets within newness threshold.')

    # Update DB
    solved_failures = []
    with get_db_connection(local=use_local_db) as con:
        for dataset, failures in failures_by_dataset.items():
            print(f'Inserting data into core table: {dataset}')
            print(f'- This will address the following failures:\n{failures}')
            df = pd.read_csv(dataset_path_map[dataset])
            df['codeset_id'] = df['codeset_id'].apply(lambda x: str(x).split('.')[0] if x else '')  # couldn't int cuz nan's
            for failure in failures:
                rows = df[df['codeset_id'] == failure['primary_key']].to_dict('records')
                # todo: if not rows, update comment that tried to fix but couldn't find any data?
                if rows:
                    insert_from_dicts(con, dataset, rows)
                    solved_failures.append(failure)
        refresh_termhub_core_cset_derived_tables(con, SCHEMA)

    # Update fetch_audit status
    fetch_status_set_success(solved_failures)


# todo: Ideally allow for output_dir for testing purposes etc, but datasets.py currently supports only 1 of 2 outdirs
#  needed. See 'todo' above its cli() func.
def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='Resolve fetch failures.', description=DESC)
    parser.add_argument(
        '-l', '--use-local-db', action='store_true', default=False, required=False,
        help='Use local database instead of server.')
    parser.add_argument(
        '-c', '--cached-dataset-threshold-hours', required=False, default=0,
        help='Threshold, in hours, until cached datasets considered invalid and need to be re-downloaded.')

    resolve_fetch_failures_excess_items(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
