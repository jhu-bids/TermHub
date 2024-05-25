#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

# TODO: get rid of unnamed row number at start of csv files
"""
import os
import re
import shutil
import sys
import tempfile
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
import pyarrow.parquet as pq
from typeguard import typechecked

from backend.db.utils import chunk_list

ENCLAVE_WRANGLER_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(ENCLAVE_WRANGLER_DIR).parent
sys.path.insert(0, str(PROJECT_ROOT))
# TODO: backend implorts: Ideally we don't want to couple with TermHub code
from backend.utils import commify, pdump
from enclave_wrangler.config import DATASET_GROUPS_CONFIG, TERMHUB_CSETS_DIR, DATASET_REGISTRY, \
    DATASET_REGISTRY_RID_NAME_MAP
from enclave_wrangler.utils import enclave_get, log_debug_info


# Don't use these headers any more. leave it to the stuff in enclave_wrangler.utils
# HEADERS = {
#     "authorization": f"Bearer {enclave_wrangler.utils.get('OTHER_TOKEN', '')}",
#     #"authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
#     #'content-type': 'application/json'
# }
DEBUG = False
CSV_DOWNLOAD_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'downloads')
CSV_TRANSFORM_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'prepped_files')
DESC = 'Tool for working w/ the Palantir Foundry enclave API. This part is for downloading enclave datasets.'
for _dir in [CSV_DOWNLOAD_DIR, CSV_TRANSFORM_DIR]:
    os.makedirs(_dir, exist_ok=True)


@typechecked
def get_transaction(dataset_rid: str, ref: str = 'master', return_field: Union[str, None] = 'rid') -> Union[str, Dict]:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/master -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    template = '{url}{dataset_rid}/transactions/{ref}'
    url = template.format(url=endpoint, dataset_rid=dataset_rid, ref=ref)

    # response = requests.get(url, headers=HEADERS,)
    response = enclave_get(url, verbose=False)
    response_json = response.json()
    if DEBUG:
        print(response_json)
    if return_field:
        return response_json[return_field]
    else:
        return response_json


@typechecked
def views2(dataset_rid: str, end_ref: str) -> [str]:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getDatasetViewFiles2
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    # curl_url = "https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100"
    if DEBUG:
        log_debug_info()
    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    url = f'{endpoint}{dataset_rid}/views2/{end_ref}/files?pageSize=100'
    response = enclave_get(url, verbose=False)
    response_json = response.json()
    file_parts = [f['logicalPath'] for f in response_json['values']]
    file_parts = [fp for fp in file_parts if re.match(r'.*part-\d\d\d\d\d', fp)]
    return file_parts


def combine_parquet_files(input_files, target_path):
    """Combine parquet files"""
    files = []
    try:
        for file_name in input_files:
            files.append(pq.read_table(file_name))
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
        print(e, file=sys.stderr)


@typechecked
def download_csv_from_parquet_parts(fav: dict, file_parts: [str], outpath: str):
    """tested with cURL:
    wget https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views/master/spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet --header "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"
    """
    dataset_rid: str = fav['rid']
    endpoint = 'https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets'
    template = '{endpoint}/{dataset_rid}/views/master/{fp}'
    with tempfile.TemporaryDirectory() as parquet_dir:
        # flush: for gh action; otherwise does not always show in the log
        print(f'\nINFO: Downloading {outpath}; tempdir {parquet_dir}, filepart endpoints:', flush=True)
        for index, fp in enumerate(file_parts):
            url = template.format(endpoint=endpoint, dataset_rid=dataset_rid, fp=fp)
            print('\t' + f'{index + 1} of {len(file_parts)}: {url}')
            response = enclave_get(url, args={'stream': True}, verbose=False)
            if response.status_code == 200:
                fname = parquet_dir + fp.replace('spark', '')
                with open(fname, "wb") as f:
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, f)
            else:
                raise RuntimeError(f'Failed opening {url} with {response.status_code}: {response.content}')

        print('INFO: Combining parquet files: Saving chunks')
        combined_parquet_fname = parquet_dir + '/combined.parquet'
        files: List[str] = []
        for file_name in os.listdir(parquet_dir):
            files.append(os.path.join(parquet_dir, file_name))

        df = pd.DataFrame()
        chunk_paths = []
        # todo: why don't we just convert parquet to csv one at a time? change chunk_list n?
        # chunks = chunk_list(files, 5)  # chunks size 5: arbitrary
        chunks = chunk_list(files, len(files))
        # Chunked to avoid memory issues w/ GitHub Action.
        for chunk_n, chunk in enumerate(chunks):
            if chunk[0].endswith('.parquet'):
                combine_parquet_files(chunk, combined_parquet_fname)
                df = pd.read_parquet(combined_parquet_fname)
            elif chunk[0].endswith('.csv'):
                if len(chunk) != 1:
                    raise RuntimeError(f"with csv, only expected one file; got: [{', '.join(chunk)}]")
                df = pd.read_csv(chunk[0], names=fav['column_names'])
            else:
                raise RuntimeError(f"unexpected file(s) downloaded: [{', '.join(chunk)}]")
            if outpath:
                os.makedirs(os.path.dirname(outpath), exist_ok=True)
                outpath_i = outpath.replace('.csv', f'_{chunk_n}.csv')
                chunk_paths.append(outpath_i)
                df.to_csv(outpath_i, index=False)

        print('INFO: Combining parquet files: Combining chunks')
        if outpath:
            df = pd.concat([pd.read_csv(path) for path in chunk_paths])
            df.to_csv(outpath, index=False)
            for path in chunk_paths:
                os.remove(path)

        print(f'Downloaded {os.path.basename(outpath)}, {commify(len(df))} records\n')
        return df


# todo: for this and alltransform_* funcs. They have a common pattern, especially first couple lines. Can we refactor?
def transform_dataset__concept_set_version_item(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_set_version_item.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df['codeset_id'] = df['codeset_id'].apply(lambda x: str(x).split('.')[0] if x else '')
    df = transforms_common(df, dataset_name)
    return df

def transform_dataset__concept_relationship(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_relationship.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    # Filter
    df2 = df[df['relationship_id'] == 'Subsumes']
    df2.to_csv(os.path.join(CSV_TRANSFORM_DIR, 'concept_relationship_subsumes_only.csv'), index=False)
    return df


def transform_dataset__concept(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__concept_ancestor(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_ancestor.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__concept_set_members(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(
        os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'),
        # dtype={'archived': bool},    # doesn't work because of missing values
        converters={'archived': lambda x: True if x == 'True' else False},  # this makes it a bool field
        keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__code_sets(dataset_name: str) -> pd.DataFrame:
    """Transformations to code_sets.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    return df


def transforms_common(df: pd.DataFrame, dataset_name) -> pd.DataFrame:
    """Common transformations"""
    # - Removed 'Unnamed' columns
    for col in [x for x in list(df.columns) if x.startswith('Unnamed')]:  # e.g. 'Unnamed: 0'
        df.drop(col, axis=1, inplace=True)
    df.sort_values(DATASET_REGISTRY[dataset_name]['sort_idx'], inplace=True)
    return df


# TODO: currently overwrites if download is newer than prepped. should also overwrite if dependency
#   prepped files are newer than this
def transform(dataset_config: dict):
    """Data transformations

    The input/outputs of this function are files. It reads the filename from `dataset_config`, then reads that file,
    transforms, and writes back to that file."""
    dataset_name: str = dataset_config['name']
    print(f'INFO: Transforming: {dataset_name}')
    inpath = os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv')
    outpath = os.path.join(CSV_TRANSFORM_DIR, dataset_name + '.csv')
    if os.path.exists(outpath) and os.path.getctime(inpath) < os.path.getctime(outpath):
        print(f'Skipping {dataset_name}: transformed file is newer than downloaded file. If you really want to transform again, delete {outpath} and try again.')
        return pd.DataFrame()
        pass


    dataset_funcs = {  # todo: using introspection, can remove need for this if function names are consistent w/ files
        # skip filtering for now
        # 'concept': transform_dataset__concept,
        'concept_set_members': transform_dataset__concept_set_members,
        'concept_relationship': transform_dataset__concept_relationship,
        'concept_ancestor': transform_dataset__concept_ancestor,
        'code_sets': transform_dataset__code_sets,
        'concept_set_version_item': transform_dataset__concept_set_version_item,
    }
    func = dataset_funcs.get(dataset_name, '')

    if func:
        df = func(dataset_name)
    else:
        converters = dataset_config.get('converters') or {}
        df = pd.read_csv(inpath, keep_default_na=False, converters=converters).fillna('')
        df = transforms_common(df, dataset_name)

    df.to_csv(outpath, index=False)
    return df


def get_datetime_dataset_last_updated(identifier: str) -> str:
    """Get timestamp of when dataset whas last updated

    :param identifier: Either (a) an RID (Reference ID) or (b) the name of a dataset, e.g. 'concept_ancestor', or (c)
    the name of a TermHub dataset group, i.e. 'counts' or 'vocab'. If 'c', a dataset from that group will be chosen as
    representative. If 'b', the name will be looked up in FAVORITE_DATASETS to get its RID.

    Resources:
     https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction
     https://unite.nih.gov/workspace/documentation/developer/api/catalog/objects/com.palantir.foundry.catalog.api.transactions.Transaction"""
    rid = identifier if identifier.startswith('ri.foundry.main.dataset.') else None
    if not rid:
        dataset_group = identifier if identifier in ('vocab', 'counts') else None
        dataset_name = DATASET_GROUPS_CONFIG[dataset_group]['last_updated_enclave_representative_table'] if dataset_group else identifier
        rid = DATASET_REGISTRY[dataset_name]['rid']
    ref = 'master'
    transaction = get_transaction(rid, ref, return_field=None)
    # pdump(transaction)
    if transaction['status'] != 'COMMITTED':
        pdump(transaction)
        raise 'status of transaction not COMMITTED. not sure what this means'
    return transaction['startTime']


def download_and_transform(
    dataset_name: str = None, dataset_rid: str = None, ref: str = 'master', output_dir: str = None, outpath: str = None,
    transforms_only=False, dataset_config: Dict = None, force_if_exists=True
):
    """Download dataset & run transformations"""
    print(f'INFO: Downloading: {dataset_name}')
    dataset_rid = DATASET_REGISTRY[dataset_name]['rid'] if not dataset_rid else dataset_rid
    dataset_name = DATASET_REGISTRY_RID_NAME_MAP[dataset_rid] if not dataset_name else dataset_name
    dataset_config = dataset_config if dataset_config else DATASET_REGISTRY[dataset_name]

    # Download
    if not transforms_only:
        # todo: would be good to accept either 'outdir' or 'outpath'.
        if not outpath:
            outpath = os.path.join(output_dir, f'{dataset_name}.csv') if output_dir else None
        if os.path.exists(outpath) and not force_if_exists:
            t = time.ctime(os.path.getmtime(outpath))
            print(f'Skipping {os.path.basename(outpath)}: {t}, {os.path.getsize(outpath)} bytes.')
        else:
            if os.path.exists(outpath):
                t = time.ctime(os.path.getmtime(outpath))
                print(f'Clobbering {os.path.basename(outpath)}: {t}, {os.path.getsize(outpath)} bytes.')
            end_ref = get_transaction(dataset_rid, ref)
            args = {'dataset_rid': dataset_rid, 'end_ref': end_ref}
            file_parts = views2(**args)
            # asyncio.run(download_and_combine_dataset_parts(dataset_rid, file_parts))
            download_csv_from_parquet_parts(dataset_config, file_parts, outpath=outpath)

    # Transform
    transform(dataset_config)


def download_datasets(
    outdir: str = CSV_DOWNLOAD_DIR, transforms_only=False, specific=[], force_if_exists=True, single_group=None
):
    """Download datasets
    :param specific: If passed, will only download datasets whose names are in this list.
    :param single_group: If passed, will only download datasets that are in this group.

    todo: speed up usinc async: https://stackoverflow.com/a/33399896/5258518"""
    if specific and single_group:
        raise ValueError('Cannot pass both "specific" and "single_group" arguments.')
    configs = DATASET_REGISTRY.values()
    datasets_configs: List[Dict] =  [x for x in configs if single_group in x['dataset_groups']] if single_group \
        else [x for x in configs if x['name'] in specific] if specific \
        else configs
    for conf in datasets_configs:
        download_and_transform(
            dataset_config=conf, dataset_name=conf['name'], outpath=os.path.join(outdir, conf['name'] + '.csv'),
            transforms_only=transforms_only, force_if_exists=force_if_exists)

# todo: ideally would allow user to select output dir that contains both CSV_DOWNLOAD_DIR and CSV_TRANSFORM_DIR
def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = ArgumentParser(prog='Dataset downloader', description=DESC)
    # parser.add_argument(
    #     '-a', '--auth_token_env_var',
    #     default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
    #     help='Name of the environment variable holding the auth token you want to use')
    parser.add_argument(
        '-n', '--dataset-name', nargs='+', default=[], required=False,
        help='Name of enclave dataset you want to download. Saved to `termhub-csets/` by default. '
             'Not needed if using --dataset-rid.')
    parser.add_argument(
        '-i', '--dataset-rid', required=False,
        help='RID of enclave dataset you want to download. Not needed if using --dataset-name.')
    parser.add_argument(
        '-r', '--ref', default='master', required=False,
        help='Should be the branch of the dataset -- I think. Refer to API documentation at '
             'https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction')
    parser.add_argument(
        '-f', '--favorites', required=False,
        default=False, action='store_true',
        help='Just download all the datasets in the enclave_wrangler.config:DATASET_REGISTRY.')
    parser.add_argument(
        '-t', '--transforms-only', default=False, action='store_true', required=False,
        help='When present, will only apply data transformations to datasets. Will not download updates.')
    parser.add_argument(
        '-o', '--output_dir', default=CSV_DOWNLOAD_DIR, required=False,
        help='Path to folder where you want output files, if there are any')
    kwargs = parser.parse_args()
    d: Dict = vars(kwargs)

    if d['favorites']:
        download_datasets(outdir=d['output_dir'], transforms_only=d['transforms_only'], specific=d['dataset_name'])
    else:
        del d['favorites']
        download_and_transform(**d)

if __name__ == '__main__':
    cli()
