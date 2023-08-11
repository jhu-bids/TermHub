#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

# TODO: get rid of unnamed row number at start of csv files
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

from typing import Dict, List, Union
from typeguard import typechecked
import os
import re
import pandas as pd
import tempfile
# import pyarrow as pa
import pyarrow.parquet as pq
# import asyncio
import shutil
import time

ENCLAVE_WRANGLER_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(ENCLAVE_WRANGLER_DIR).parent
sys.path.insert(0, str(PROJECT_ROOT))
# TODO: backend implorts: Ideally we don't want to couple with TermHub code
from backend.db.utils import chunk_list
from backend.utils import commify, pdump
from enclave_wrangler.config import TERMHUB_CSETS_DIR, FAVORITE_DATASETS, FAVORITE_DATASETS_RID_NAME_MAP
from enclave_wrangler.utils import enclave_get, log_debug_info


# Don't use these headers any more. leave it to the stuff in enclave_wrangler.utils
# HEADERS = {
#     "authorization": f"Bearer {enclave_wrangler.utils.get('OTHER_TOKEN', '')}",
#     #"authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
#     #'content-type': 'application/json'
# }
DEBUG = False
# TODO: Once git LFS set up, dl directly to datasets folder, or put these in raw/ and move csvs_repaired to datasets/
CSV_DOWNLOAD_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'downloads')
CSV_TRANSFORM_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'prepped_files')
DESC = 'Tool for working w/ the Palantir Foundry enclave API. This part is for downloading enclave datasets.'
os.makedirs(CSV_TRANSFORM_DIR, exist_ok=True)


@typechecked
def getTransaction(dataset_rid: str, ref: str = 'master', return_field: Union[str, None] = 'rid') -> Union[str, Dict]:
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
def views2(dataset_rid: str, endRef: str) -> [str]:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getDatasetViewFiles2
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    curl_url = "https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100"

    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    template = '{endpoint}{dataset_rid}/views2/{endRef}/files?pageSize=100'
    url = template.format(endpoint=endpoint, dataset_rid=dataset_rid, endRef=endRef)

    response = enclave_get(url, verbose=False)
    response_json = response.json()
    file_parts = [f['logicalPath'] for f in response_json['values']]
    file_parts = [fp for fp in file_parts if re.match('.*part-\d\d\d\d\d', fp)]
    return file_parts


@typechecked
def download_and_combine_dataset_parts(fav: dict, file_parts: [str], outpath: str) -> pd.DataFrame:
    """tested with cURL:
    wget https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views/master/spark%2Fpart-00000-c94edb9f-1221-4ae8-ba74-58848a4d79cb-c000.snappy.parquet --header "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"
    """
    dataset_rid: str = fav['rid']
    endpoint = 'https://unite.nih.gov/foundry-data-proxy/api/dataproxy/datasets'
    template = '{endpoint}/{dataset_rid}/views/master/{fp}'
    # if DEBUG:

    # download parquet files
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
        # TODO: why don't we just convert parquet to csv one at a time?
        # TODO: Changing this to see if helps
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

    # JOIN & Filter
    try:
        csm_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'concept_set_members.csv'), keep_default_na=False).fillna('')
        # JOIN
        cr_csm = df.merge(csm_df, left_on='concept_id_1', right_on='concept_id')
        # Filter
        df = df[df['concept_id_1'].isin(cr_csm['concept_id_1'])]
    except FileNotFoundError:
        print('Warning: Tried transforming concept_relationship.csv, but concept_set_members.csv must be downloaded '
              'and transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    # Filter
    df2 = df[df['relationship_id'] == 'Subsumes']
    df2.to_csv(os.path.join(CSV_TRANSFORM_DIR, 'concept_relationship_subsumes_only.csv'), index=False)

    return df


def transform_dataset__concept(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)

    # JOIN
    try:
        csm_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'concept_set_members.csv'), keep_default_na=False).fillna('')
        concept_csm = df.merge(csm_df, on='concept_id')
        df = df[df['concept_id'].isin(concept_csm['concept_id'])]
    except FileNotFoundError:
        print('Warning: Tried transforming concept.csv, but concept_set_members.csv must be downloaded and transformed '
              'first. Try running again after this process completes. Eventually need to do these transformations '
              'dependency ordered fashion.', file=sys.stderr)

    return df


def transform_dataset__concept_ancestor(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_ancestor.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)

    # JOIN
    try:
        csm_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'concept_set_members.csv'), keep_default_na=False).fillna('')
        ca_csm = df.merge(csm_df, left_on='ancestor_concept_id', right_on='concept_id')
        df = df[df['ancestor_concept_id'].isin(ca_csm['ancestor_concept_id'])]
    except FileNotFoundError:
        print('Warning: Tried transforming concept_ancestor.csv, but concept_set_members.csv must be downloaded and '
              'transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    return df


def transform_dataset__concept_set_members(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(
        os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'),
        # dtype={'archived': bool},    # doesn't work because of missing values
        converters={'archived': lambda x: True if x == 'True' else False},  # this makes it a bool field
        keep_default_na=False).fillna('')
    # JOIN
    try:
        # Note: Depends on `code_sets.csv` now -- don't load concept_set_members unless codeset exists
        # don't have to do that anymore, I think
        cs_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'code_sets.csv'), keep_default_na=False).fillna('')
        codeset_ids = set(cs_df['codeset_id'])
        df = df[df['codeset_id'].isin(codeset_ids)]
    except FileNotFoundError:
        print('Warning: Tried transforming code_sets.csv, but concept_set_container.csv must be downloaded and '
              'transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__code_sets(dataset_name: str) -> pd.DataFrame:
    """Transformations to code_sets.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)

    # JOIN
    try:
        # Note: Depends on `concept_set_container.csv` -- don't load code_sets unless container exists
        # Note: Depends on `concept_set_container.csv`, but there is no transform for it. So, read from DL dir.
        # don't have to do that anymore, I think
        csc_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'concept_set_container.csv'), keep_default_na=False).fillna('')
        container_concept_set_name_ids = set(csc_df['concept_set_id'])
        df = df[df['concept_set_name'].isin(container_concept_set_name_ids)]
    except FileNotFoundError:
        print('Warning: Tried transforming code_sets.csv, but concept_set_container.csv must be downloaded and '
              'transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    return df


def transforms_common(df: pd.DataFrame, dataset_name) -> pd.DataFrame:
    """Common transformations"""
    # - Removed 'Unnamed' columns
    for col in [x for x in list(df.columns) if x.startswith('Unnamed')]:  # e.g. 'Unnamed: 0'
        df.drop(col, axis=1, inplace=True)
    df.sort_values(FAVORITE_DATASETS[dataset_name]['sort_idx'], inplace=True)

    return df


# TODO: currently overwrites if download is newer than prepped. should also overwrite if dependency
#   prepped files are newer than this
def transform(fav: dict) -> pd.DataFrame:
    """Data transformations"""
    dataset_name: str = fav['name']
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
        converters = fav.get('converters') or {}
        df = pd.read_csv(inpath, keep_default_na=False, converters=converters).fillna('')
        df = transforms_common(df, dataset_name)

    df.to_csv(outpath, index=False)
    return df


def get_last_vocab_update():
    """
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/objects/com.palantir.foundry.catalog.api.transactions.Transaction
    """
    dataset_rid = FAVORITE_DATASETS['concept']['rid']
    ref = 'master'
    transaction = getTransaction(dataset_rid, ref, return_field=None)
    # pdump(transaction)
    if transaction['status'] != 'COMMITTED':
        pdump(transaction)
        raise 'status of transaction not COMMITTED. not sure what this means'
    return transaction['startTime']
# print(get_last_vocab_update())
# exit()


def download_and_transform(
    dataset_name: str = None, dataset_rid: str = None, ref: str = 'master', output_dir: str = None, outpath: str = None,
    transforms_only=False, fav: Dict = None, force_if_exists=True
) -> pd.DataFrame:
    """Download dataset & run transformations"""
    print(f'INFO: Downloading: {dataset_name}')
    dataset_rid = FAVORITE_DATASETS[dataset_name]['rid'] if not dataset_rid else dataset_rid
    dataset_name = FAVORITE_DATASETS_RID_NAME_MAP[dataset_rid] if not dataset_name else dataset_name
    fav = fav if fav else FAVORITE_DATASETS[dataset_name]

    # Download
    df = pd.DataFrame()
    if not transforms_only:
        # todo: Temp: would be good to accept either 'outdir' or 'outpath'.
        if not outpath:
            outpath = os.path.join(output_dir, f'{dataset_name}.csv') if output_dir else None
        if os.path.exists(outpath) and not force_if_exists:
            t = time.ctime(os.path.getmtime(outpath))
            print(f'Skipping {os.path.basename(outpath)}: {t}, {os.path.getsize(outpath)} bytes.')
        else:
            if os.path.exists(outpath):
                t = time.ctime(os.path.getmtime(outpath))
                print(f'Clobbering {os.path.basename(outpath)}: {t}, {os.path.getsize(outpath)} bytes.')
            end_ref = getTransaction(dataset_rid, ref)
            args = {'dataset_rid': dataset_rid, 'endRef': end_ref}
            file_parts = views2(**args)
            # asyncio.run(download_and_combine_dataset_parts(dataset_rid, file_parts))
            df: pd.DataFrame = download_and_combine_dataset_parts(fav, file_parts, outpath=outpath)

    # Transform
    df2: pd.DataFrame = transform(fav)

    return df2 if len(df2) > 0 else df


def download_datasets(
    outdir: str = CSV_DOWNLOAD_DIR, transforms_only=False, specific=[], force_if_exists=True, single_group=None
):
    """Download datasets
    :param specific: If not passed, will download all favorite datasets"""
    for fav in FAVORITE_DATASETS.values():
        if single_group and single_group not in fav['dataset_groups']:
            continue
        if not specific or fav['name'] in specific:
            outpath = os.path.join(outdir, fav['name'] + '.csv')
            download_and_transform(fav=fav, dataset_name=fav['name'], outpath=outpath, transforms_only=transforms_only,
                                   force_if_exists=force_if_exists)

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
        help='Just download all the datasets that are currently hardcoded as "favorites".')
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
