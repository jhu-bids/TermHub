#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
from argparse import ArgumentParser
from typing import Dict

# dataset download API, three steps:
steps = [
    {'endpoint':    'https://unite.nih.gov/foundry-catalog/api/catalog/datasets/transactions/master',
     'params':      '-H "authorization: Bearer $OTHER_TOKEN"',
     'api-docs':    ''
    } ,
    {}
]
def download(rid, output_dir=None):
    """download a dataset from the enclave"""

    # curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772/transactions/master -H "authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN" | json_pp
    # curl https://unite.nih.gov/foundry-catalog/api/catalog/datasets/ri.foundry.main.dataset.47a26e85-307e-4a21-9583-f58c90b73455/transactions/master -H "authorization: Bearer $OTHER_TOKEN" | json_pp

    url = f'https://unite.nih.gov/actions/'
    header = f'Authentication: Bearer 1351351351t3135dfadgaddt'
    response = requests.post(url, data=cs_create_data)

    r = response.json()
    return r


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API.'
                          'This part is for downloading enclave datasets.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-o', '--output_dir',
        help='Path to folder where you want output files, if there are any')

    parser.add_argument(
        '--rid',
        help='Rid of enclave dataset you want to download. Use -o to specify output directory, or who knows '
             'where it will end up.')

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)

    if kwargs_dict['dataset-download'] is not None:
        download(**kwargs_dict) # i don't know how to fit this into main.py...it could go somewhere else. Or I could
                                # skip the whole get args thing and just write a separate standalone py file here
        return

    download(**kwargs_dict)


if __name__ == '__main__':
    cli()
