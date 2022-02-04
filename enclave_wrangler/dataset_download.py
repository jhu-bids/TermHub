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
def getTransaction(datasetRid: str, ref: str = 'master') -> dict:
    """API documentation at https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction
    tested with curl:
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/master -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.47a26e85-307e-4a21-9583-f58c90b73455/transactions/master -H "authorization: Bearer $OTHER_TOKEN" | json_pp
    """
    if DEBUG:
        log_debug_info()

    endpoint = 'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/transactions/master/'
    template = '{url}{datasetRid}/transactions/{ref}'
    url = template.format(url=endpoint, datasetRid=datasetRid, ref=ref)

    response = requests.get(url, headers=HEADERS,)
    response_json = response.json()
    print(response_json)
    return response_json

def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API. ' \
          'This part is for downloading enclave datasets.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-o', '--output_dir',
        help='Path to folder where you want output files, if there are any')

    parser.add_argument(
        '--datasetRid',
        help='RID of enclave dataset you want to download. Use -o to specify output directory, or who knows '
             'where it will end up.')

    parser.add_argument(
        '--ref',
        default='master',
        help='Should be the branch of the dataset -- I think. Refer to API documentation at '
                'https://unite.nih.gov/workspace/documentation/developer/api/catalog/services/CatalogService/endpoints/getTransaction')

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    # if kwargs_dict['dataset-download'] is not None:
    args = {key: kwargs_dict[key] for key in ['datasetRid','ref']}
    getTransaction(**args)
    return

if __name__ == '__main__':
    cli()
