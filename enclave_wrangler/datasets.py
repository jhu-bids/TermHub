#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download."""
from argparse import ArgumentParser

from typing import Dict
from typeguard import typechecked
import os
import requests
import pandas as pd
import tempfile
# import pyarrow as pa
import pyarrow.parquet as pq
# import asyncio
import shutil
import time

from enclave_wrangler.config import config
from enclave_wrangler.utils import log_debug_info

from enclave_wrangler.config import FAVORITE_DATASETS

# TODO: get rid of unnamed row number at start of csv files

HEADERS = {
    "authorization": f"Bearer {config['OTHER_TOKEN']}",
    #"authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    #'content-type': 'application/json'
}
DEBUG = False
TARGET_CSV_DIR='termhub-csets/datasets'


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
    if DEBUG:
        print(response_json)
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
def download_and_combine_dataset_parts(datasetRid: str, file_parts: [str], outpath: str) -> pd.DataFrame:
    """tested with cURL:
    wget https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views/master/spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet --header "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"
    """
    endpoint = 'https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets'
    template = '{endpoint}/{datasetRid}/views/master/{fp}'
    # if DEBUG:

    # download parquet files
    with tempfile.TemporaryDirectory() as parquet_dir:
        # if DEBUG:
        print(f'\nDownloading {outpath}; tempdir {parquet_dir}, filepart endpoints:')
        for fp in file_parts:
            url = template.format(endpoint=endpoint, datasetRid=datasetRid, fp=fp)
            print('\t' + url)
            response = requests.get(url, headers=HEADERS, stream=True)
            if response.status_code == 200:
                fname = parquet_dir + fp.replace('spark', '')
                with open(fname, "wb") as f:
                    response.raw.decode_content = True
                    # print(f'{fname} copying {time.strftime("%X")} ---> ', end='')
                    shutil.copyfileobj(response.raw, f)
                # TODO: @Siggie: part_df unused. `parquet_parts` in 'except' block doesn't exist and comes after raise
                #       @Joe: not sure why -- I'm trying commenting it out
                # try:
                #     print(f'reading {time.strftime("%X")} ---> ', end='')
                #     part_df = pd.read_parquet(fname)
                #     print(f'read {time.strftime("%X")}')
                # except Exception as e:
                #     print(f'errored {time.strftime("%X")} ----> {e}')
                #     raise e
                #     parquet_parts.append(fname)
            else:
                raise f'failed opening {url} with {response.status_code}: {response.content}'
        combined_parquet_fname = parquet_dir + '/combined.parquet'
        combine_parquet_files(parquet_dir, combined_parquet_fname)
        df = pd.read_parquet(combined_parquet_fname)
        if outpath:
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            df.to_csv(outpath, index=False)
        return df


def combine_parquet_files(input_folder, target_path):
    try:
        files = []
        for file_name in os.listdir(input_folder):
            files.append(pq.read_table(os.path.join(input_folder, file_name)))

        with pq.ParquetWriter(
            target_path,
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


def run(
        datasetRid: str, ref: str = 'master', outdir: str = None, outpath: str = None, transforms_only=False
) -> pd.DataFrame:
    # TODO: Temp: would be good to accept either 'outdir' or 'outpath'.
    if not outpath:
        outpath = os.path.join(outdir, f'{datasetRid}__{ref}.csv') if outdir else None
    if os.path.exists(outpath):
        t = time.ctime(os.path.getmtime(outpath))
        print(f'Skipping {outpath}: {t}, {os.path.getsize(outpath)} bytes.')
        return pd.read_csv(outpath)
    endRef = getTransaction(datasetRid, ref)
    args = {'datasetRid': datasetRid, 'endRef': endRef}
    file_parts = views2(**args)
    df: pd.DataFrame = download_and_combine_dataset_parts(datasetRid, file_parts, outpath=outpath)
    # asyncio.run(download_and_combine_dataset_parts(datasetRid, file_parts))
    return df


def favorite_updates__concept(df: pd.DataFrame):
    """Updates to the `concept` table prior to downloading."""

    return df


def download_favorites(outdir: str = TARGET_CSV_DIR):
    """Download favorite datasets"""
    for fav in FAVORITE_DATASETS.values():
        outpath = os.path.join(outdir, fav['name'] + '.csv')
        df: pd.DataFrame = run(datasetRid=fav['rid'], outpath=outpath)
        if fav['name'] == 'concept':
            df = favorite_updates__concept(df)
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
        '-n', '--datasetName',
        help='Name of enclave dataset you want to download. CSV will be saved to ValueSet-Tools/data/datasets/<name>')

    parser.add_argument(
        '-i', '--datasetRid',
        help='RID of enclave dataset you want to download.')
    parser.add_argument(
        '-r', '--ref',
        default='master',
        help='Should be the branch of the dataset -- I think. Refer to API documentation at '
                'https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction')
    parser.add_argument(
        '-f', '--favorites',
        default=False, action='store_true',
        help='Just download all the datasets that are currently hardcoded as "favorites".')
    parser.add_argument(
        '-t', '--transforms-only',
        default=False, action='store_true',
        help='When present, will only apply data transformations to datasets. Will not download updates.')
    parser.add_argument(
        '-o', '--output_dir',
        default=FAVORITE_DATASETS,
        help='Path to folder where you want output files, if there are any')

    return parser

def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    d: Dict = vars(kwargs)

    # Run
    if d['favorites']:
        download_favorites(outdir=d['output_dir'], transforms_only=d['transforms_only'])
    else:
        args = {key: d[key] for key in ['datasetRid','ref']}
        run(**args)

if __name__ == '__main__':
    cli()
