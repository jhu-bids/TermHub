#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
from argparse import ArgumentParser
from typing import Dict

import requests
from typing import Dict
from typeguard import typechecked
import json
import os
from datetime import datetime, timezone
import requests
import pandas as pd

from enclave_wrangler.config import config
from enclave_wrangler.utils import log_debug_info

HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    #'content-type': 'application/json'
}
DEBUG = False


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
    print(response_json)
    return response_json['rid']

@typechecked
def views2(datasetRid: str, endRef: str) -> dict:
    """API documentation at
    https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getDatasetViewFiles2
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/views2/ri.foundry.main.transaction.00000022-85ed-47eb-9eeb-959737c88847/files?pageSize=100 -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    """
    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/'
    template = '{url}{datasetRid}/views2/{endRef}?pageSize=100'
    url = template.format(url=endpoint, datasetRid=datasetRid, endRef=endRef)

    response = requests.get(url, headers=HEADERS,)
    response_json = response.json()
    print(response_json)
    return response_json['rid']


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
        '--datasetRid',
        help='RID of enclave dataset you want to download. Use -o to specify output directory, or who knows '
             'where it will end up.')

    parser.add_argument(
        '--ref',
        default='master',
        help='Should be the branch of the dataset -- I think. Refer to API documentation at '
                'https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction')

    parser.add_argument(
        '-o', '--output_dir',
        help='Path to folder where you want output files, if there are any')

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    # if kwargs_dict['dataset-download'] is not None:
    args = {key: kwargs_dict[key] for key in ['datasetRid','ref']}
    endRef = getTransaction(**args)
    args = {'datasetRid': kwargs_dict['datasetRid'], 'endRef': endRef}
    file_parts = views2(**args)
    return

if __name__ == '__main__':
    cli()
