#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

# TODO: get rid of unnamed row number at start of csv files
"""
import sys
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

from enclave_wrangler.config import config, TERMHUB_CSETS_DIR, FAVORITE_DATASETS, FAVORITE_DATASETS_RID_NAME_MAP
from enclave_wrangler.utils import log_debug_info

HEADERS = {
    "authorization": f"Bearer {config['OTHER_TOKEN']}",
    #"authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    #'content-type': 'application/json'
}
DEBUG = False
# TODO: Once git LFS set up, dl directly to datasets folder, or put these in raw/ and move csvs_repaired to datasets/
CSV_DOWNLOAD_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'downloads')
CSV_TRANSFORM_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'prepped_files')
os.makedirs(CSV_TRANSFORM_DIR, exist_ok=True)


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


def transform_dataset__concept_relationship(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_relationship.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')

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

    df = transforms_common(df, dataset_name)

    # Subsumes only:
    df2 = df[df['relationship_id'] == 'Subsumes']
    # df2.sort_values(['concept_id_1', 'concept_id_2'], inplace=True) shouldn't be necessary
    df2.to_csv(os.path.join(CSV_TRANSFORM_DIR, 'concept_relationship_subsumes_only.csv'), index=False)

    return df


def transform_dataset__concept(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)
    # for now just save whole thing

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

    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__concept_ancestor(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept_ancestor.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')

    # JOIN
    try:
        csm_df = pd.read_csv(
            os.path.join(CSV_TRANSFORM_DIR, 'concept_set_members.csv'), keep_default_na=False).fillna('')

        ancestor_is_csm = df.merge(csm_df, left_on='ancestor_concept_id', right_on='concept_id')
        descendant_is_csm = df.merge(csm_df, left_on='descendant_concept_id', right_on='concept_id')

        dfa = df[df['ancestor_concept_id'].isin(ancestor_is_csm['ancestor_concept_id'])]
        dfd = df[df['descendant_concept_id'].isin(descendant_is_csm['descendant_concept_id'])]

        df = pd.concat([dfa, dfd]).drop_duplicates().reset_index(drop=True)

    except FileNotFoundError:
        print('Warning: Tried transforming concept_ancestor.csv, but concept_set_members.csv must be downloaded and '
              'transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    df = transforms_common(df, dataset_name)
    return df


def transform_dataset__concept_set_members(dataset_name: str) -> pd.DataFrame:
    """Transformations to concept.csv"""
    df = pd.read_csv(
        os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'),
        # dtype={'archived': bool},    # doesn't work because of missing values
        converters={'archived': lambda v: v and True or False},  # this makes it a bool field
        keep_default_na=False).fillna('')
    df = transforms_common(df, dataset_name)

    return df


def transform_dataset__code_sets(dataset_name: str) -> pd.DataFrame:
    """Transformations to code_sets.csv"""
    df = pd.read_csv(os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv'), keep_default_na=False).fillna('')

    # JOIN
    try:
        # Note: Depends on `concept_set_container_edited.csv`, but there is no transform for it. So, read from DL dir.
        csc_df = pd.read_csv(
            os.path.join(CSV_DOWNLOAD_DIR, 'concept_set_container_edited.csv'), keep_default_na=False).fillna('')
        container_concept_set_name_ids = set(csc_df['concept_set_id'])
        df = df[df['concept_set_name'].isin(container_concept_set_name_ids)]
    except FileNotFoundError:
        print('Warning: Tried transforming code_sets.csv, but concept_set_container_edited.csv must be downloaded and '
              'transformed first. Try running again after this process completes. Eventually need to do these '
              'transformations dependency ordered fashion.', file=sys.stderr)

    df = transforms_common(df, dataset_name)
    return df


def transforms_common(df: pd.DataFrame, dataset_name) -> pd.DataFrame:
    """Common transformations"""
    # - Removed 'Unnamed' columns
    for col in [x for x in list(df.columns) if x.startswith('Unnamed')]:  # e.g. 'Unnamed: 0'
        df.drop(col, axis=1, inplace=True)
    df.sort_values(FAVORITE_DATASETS[dataset_name]['sort_idx'], inplace=True)

    return df


def transform(dataset_name: str) -> pd.DataFrame:
    ipath = os.path.join(CSV_DOWNLOAD_DIR, dataset_name + '.csv')
    opath = os.path.join(CSV_TRANSFORM_DIR, dataset_name + '.csv')
    if os.path.exists(opath) and os.path.getctime(ipath) < os.path.getctime(opath):
        print(f'transformed file is newer than downloaded file. If you really want to transform again, delete {opath} and try again.')
        return pd.DataFrame()

    """Data transformations"""
    dataset_funcs = {  # todo: using introspection, can remove need for this if function names are consistent w/ files
        # for now try not filtering concept, concept_relationship, and concept_ancestor because the filtering was
        #       making some weird stuff happen -- concepts in csets not showing up in comparison list because of
        #       not being in concept_relationship maybe
        # 'concept': transform_dataset__concept,
        'concept_set_members': transform_dataset__concept_set_members,
        # 'concept_relationship': transform_dataset__concept_relationship,
        # 'concept_ancestor': transform_dataset__concept_ancestor,
        'code_sets': transform_dataset__code_sets,
    }
    func = dataset_funcs.get(dataset_name, '')

    print(f'transforming {dataset_name}')
    if func:
        df = func(dataset_name)
    else:
        df = pd.read_csv(ipath, keep_default_na=False).fillna('')
        df = transforms_common(df, dataset_name)

    df.to_csv(opath, index=False)
    return df


def run(
    dataset_name: str = None, dataset_rid: str = None, ref: str = 'master', outdir: str = None, outpath: str = None,
    transforms_only=False
) -> pd.DataFrame:
    dataset_rid = FAVORITE_DATASETS[dataset_name]['rid'] if not dataset_rid else dataset_rid
    dataset_name = FAVORITE_DATASETS_RID_NAME_MAP[dataset_rid] if not dataset_name else dataset_name

    # Download
    df = pd.DataFrame()
    if not transforms_only:
        # TODO: Temp: would be good to accept either 'outdir' or 'outpath'.
        if not outpath:
            outpath = os.path.join(outdir, f'{dataset_rid}__{ref}.csv') if outdir else None
        if os.path.exists(outpath):
            t = time.ctime(os.path.getmtime(outpath))
            print(f'Skipping {outpath}: {t}, {os.path.getsize(outpath)} bytes.')
            return pd.read_csv(outpath)
        endRef = getTransaction(dataset_rid, ref)
        args = {'datasetRid': dataset_rid, 'endRef': endRef}
        file_parts = views2(**args)
        # asyncio.run(download_and_combine_dataset_parts(datasetRid, file_parts))
        df: pd.DataFrame = download_and_combine_dataset_parts(dataset_rid, file_parts, outpath=outpath)

    # Transform
    df2: pd.DataFrame = transform(dataset_name)

    return df2 if len(df2) > 0 else df


def run_favorites(outdir: str = CSV_DOWNLOAD_DIR, transforms_only=False, specific=[]):
    """Run on favorite datasets"""
    for fav in FAVORITE_DATASETS.values():
        if not specific or fav['name'] in specific:
            outpath = os.path.join(outdir, fav['name'] + '.csv')
            run(dataset_name=fav['name'], outpath=outpath, transforms_only=transforms_only)


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API. ' \
          'This part is for downloading enclave datasets.'
    parser = ArgumentParser(description=package_description)

    # parser.add_argument(
    #     '-a', '--auth_token_env_var',
    #     default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
    #     help='Name of the environment variable holding the auth token you want to use')
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
        default=CSV_DOWNLOAD_DIR,
        help='Path to folder where you want output files, if there are any')

    return parser

def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    d: Dict = vars(kwargs)

    # Run
    specific = []
    if d['datasetName']:
        specific.append(d['datasetName'])

    if d['favorites']:
        run_favorites(outdir=d['output_dir'], transforms_only=d['transforms_only'], specific=specific)
    else:
        args = {key: d[key] for key in ['datasetRid', 'ref']}
        run(**args)

if __name__ == '__main__':
    cli()
