#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
# import asyncio
import json
import os
import pandas as pd
# import pyarrow as pa
import pyarrow.parquet as pq
import requests
import tempfile
import time
import shutil
from argparse import ArgumentParser
from typeguard import typechecked
from typing import Dict

from enclave_wrangler.config import config
from enclave_wrangler.utils import log_debug_info


HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    #'content-type': 'application/json'
}
DEBUG = False
TARGET_CSV_DIR='data/datasets/'


@typechecked
def getTransaction(datasetRid: str, ref: str = 'master') -> str:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/master -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    template = '{url}{datasetRid}/transactions/{ref}'
    url = template.format(url=endpoint, datasetRid=datasetRid, ref=ref)

    response = requests.get(url, headers=HEADERS,)
    response_json = response.json()

    if response.status_code >= 400:
        raise RuntimeError(json.dumps(response_json))

    return response_json['rid']


@typechecked
def views2(datasetRid: str, endRef: str) -> [str]:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getDatasetViewFiles2
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    curl_url = "https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100"

    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    template = '{endpoint}{datasetRid}/views2/{endRef}/files?pageSize=100'
    url = template.format(endpoint=endpoint, datasetRid=datasetRid, endRef=endRef)

    response = requests.get(url, headers=HEADERS,)
    response_json = response.json()
    file_parts = [f['logicalPath'] for f in response_json['values']]
    return file_parts[1:]


@typechecked
def datasets_views(datasetRid: str, file_parts: [str]) -> pd.DataFrame:
    """tested with cURL:
    wget https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views/master/spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet --header "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"
    """

    endpoint = 'https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets'
    template = '{endpoint}/{datasetRid}/views/master/{fp}'

    # download parquet files
    with tempfile.TemporaryDirectory() as parquet_dir:
        print('created temporary directory', parquet_dir)
        parquet_parts = []
        for fp in file_parts:
            url = template.format(endpoint=endpoint, datasetRid=datasetRid, fp=fp)
            response = requests.get(url, headers=HEADERS, stream=True)
            if response.status_code == 200:
                fname = parquet_dir + fp.replace('spark', '')
                with open(fname, "wb") as f:
                    response.raw.decode_content = True
                    print(f'{fname} copying {time.strftime("%X")} ---> ', end='')
                    shutil.copyfileobj(response.raw, f)
                    # print(f'sleeping {time.strftime("%X")} ---> ', end='')
                    # await asyncio.sleep(2)
                    # print(f'waking {time.strftime("%X")} ---> ', end='')
                    print()
                try:
                    print(f'reading {time.strftime("%X")} ---> ', end='')
                    part_df = pd.read_parquet(fname)
                    print(f'read {time.strftime("%X")}')
                except Exception as e:
                    print(f'errored {time.strftime("%X")} ----> {e}')
                    raise e
                    parquet_parts.append(fname)
            else:
                raise RuntimeError(f'failed opening {url} with {response.status_code}: {response.content}')
        combined_parquet_fname = parquet_dir + '/combined.parquet'
        combine_parquet_files(parquet_dir, combined_parquet_fname)
        df = pd.read_parquet(combined_parquet_fname)
        # p1 = pd.read_parquet('./spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet')

        return df


def combine_parquet_files(input_folder, target_path):
    try:
        files = []
        for file_name in os.listdir(input_folder):
            files.append(pq.read_table(os.path.join(input_folder, file_name)))

        with pq.ParquetWriter(target_path,
                              files[0].schema,
                              version='2.0',
                              compression='gzip',
                              use_dictionary=True,
                              data_page_size=2097152,  # 2MB
                              write_statistics=True
        ) as writer:
            for f in files:
                writer.write_table(f)
    except Exception as e:
        print(e)


def cli_validate(args: Dict):
    """Validate CLI parameters"""
    # TODO: @Siggie: If we do want `--download-all-registered-datasets` as a param here, I think it would be good to
    #  throw an error like this. But if you don't want that, or if you think I need to make this message clearer, let me know. - Joe 2022/05/11
    if args['download_all_registered_datasets'] and (args['datasetName'] or args['datasetRid']):
        raise RuntimeError('Parameter (1) `--download-all-registered-datasets` was passed, but either/both (2) `--datasetName` and '
                           '`--datasetRid` were also passed. Please either pass only (1) to download all datasets, or (2) '
                           'to download 1 dataset, but not both sets of these parameters at the same time.')


def run_single(datasetRid: str, ref: str = 'master', write_csv_in_calling_dir=True) -> None:
    """Run progam"""
    endRef = getTransaction(datasetRid, ref)
    args = {'datasetRid': datasetRid, 'endRef': endRef}
    file_parts = views2(**args)
    df = datasets_views(datasetRid, file_parts)
    # asyncio.run(datasets_views(datasetRid, file_parts))
    if write_csv_in_calling_dir:
        df.to_csv()


def run_all() -> None:
    """Run progam"""
    # ref = 'master'
    # endRef = getTransaction(datasetRid, ref)
    # args = {'datasetRid': datasetRid, 'endRef': endRef}
    # file_parts = views2(**args)
    # datasets_views(datasetRid, file_parts)
    project_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
    submodule_names = ['termhub-csets', 'termhub-vocab']
    for module_dir in submodule_names:
        datasets_dir = os.path.join(project_dir, module_dir, 'datasets')
        registry_path = os.path.join(datasets_dir, 'registry.json')
        with open(registry_path, 'r') as f:
            dataset_name_rid_map: Dict[str, str] = json.load(f)
        for dataset_name, dataset_rid in dataset_name_rid_map.items():
            dataset_dir = os.path.join(datasets_dir, dataset_name)
            os.makedirs(dataset_dir, exist_ok=True)
            # TODO: Consider making subdirs: <ref>, <transaction-id>, <date>?
            #  ...And update READMEs w/ the info
            # TODO: Solve error I got with `'concept_set_version_item_rv_edited_mapped'`:
            #  {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Catalog:BranchesNotFound', 'errorInstanceId': '537796d5-230c-481c-8a45-2e56f309c3d9', 'parameters': {'datasetRids': '[ri.foundry.main.dataset.e7941080-8df0-4392-96c5-82fc2f84e2a7]', 'branchIds': '[master]'}}
            df = run_single(dataset_rid, write_csv_in_calling_dir=False)
            # TODO: Save the DF
            print()


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API. ' \
          'This part is for downloading enclave datasets.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-a', '--auth_token_env_var',
        default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
        help='Name of the environment variable holding the auth token you want to use')

    parser.add_argument(
        '--datasetName',
        help='Name of enclave dataset you want to download. CSV will be saved to ValueSet-Tools/data/datasets/<name>')

    parser.add_argument(
        '--datasetRid',
        help='RID of enclave dataset you want to download.')

    parser.add_argument(
        '--ref',
        default='master',
        help='Should be the branch of the dataset -- I think. Refer to API documentation at '
                'https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction')

    # TODO: @Siggie: I'm not sure if adding this as an option here is the best design, but it seemed like the
    #  easiest/fastest way I could think of, and probably isn't a bad way anyhow. If you approve, you can remove this
    #  comment. Otherwise, we should figure out the preferred way to implement this feature. - Joe 2022/05/11
    parser.add_argument(
        '-A', '--download-all-registered-datasets',
        action='store_true',
        help='If present, this will initiatie download of all "registered" datasets. This is tightly coupled with the '
             'environment that this dataset_download CLI is being run in. That is, it is expected that, within the same'
             'directory as `enclave_wrangler/`, there also be two additional directories / git submodules: '
             '`termhub-csets` and `termhub-vocab`. Within both of these directories, there should be a '
             '`datasets/registry.json`, which contains key-value pairs, where the values are RIDs of datasets to be '
             'downloaded from the N3C data enclave.')

#    parser.add_argument(
#        '-o', '--output_dir',
#        help='Path to folder where you want output files, if there are any')

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    cli_validate(kwargs_dict)

    if kwargs_dict['download_all_registered_datasets']:
        run_all()
    else:
        # if kwargs_dict['dataset-download'] is not None:
        args = {key: kwargs_dict[key] for key in ['datasetRid','ref']}
        # should only have -A by itself or other otpoins without -A
        run_single(**args)


if __name__ == '__main__':
    cli()
