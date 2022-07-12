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
import tempfile
# import pyarrow as pa
import pyarrow.parquet as pq
# import asyncio
import shutil
import time

from enclave_wrangler.config import config
from enclave_wrangler.utils import log_debug_info

HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    #'content-type': 'application/json'
}
DEBUG = False
# TARGET_CSV_DIR='data/datasets/'


@typechecked
def objTypes() -> [{}]:
    """API documentation at
    https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """

    ontologyRid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontologyRid}/objectTypes'
    url = f'https://{config["HOSTNAME"]}{api_path}'

    response = requests.get(url, headers=HEADERS,)
    response_json = response.json()
    print(response_json)
    # types = pd.DataFrame(data=response_json)
    return response_json['data']

def run() -> None:
    types = objTypes()
    print('\n'.join([t['apiName'] for t in types]))
    pass



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

    return parser

def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    # if kwargs_dict['dataset-download'] is not None:
    args = {key: kwargs_dict[key] for key in []} # ['datasetRid','ref']}
    run(**args)
    return

if __name__ == '__main__':
    cli()
