#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
# TODO: For some reason, 'argparse' is not available in Stephanie's Python3.9 standard library, so she has installed
#  the "ArgumentParser" class manually. However, we really want everyone to be using the same libraries, so
#  we need to find out why this is happening to her, and fix it, instead of the workaround below: - Joe 2022/02/02
#try:
#    import ArgumentParser
#except ModuleNotFoundError:
from argparse import ArgumentParser
from typing import Dict

from enclave_wrangler.main import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-p', '--input-csv-folder-path',
        help='Path to folder with 3 files that have specific columns that adhere to concept table data model. These '
             'files must have the following names: i. `code_sets.csv`, ii. `concept_set_container_edited.csv`, iii. '
             '`concept_set_version_item_rv_edited.csv`.')
    parser.add_argument(
        '-c', '--use-cache',
        action='store_true',
        help='If present, will check the input file and look at the `enclave_codeset_id` column. If no empty values are'
             ' present, this indicates that the `enclave_wrangler` has already been run and that the input file itself '
             'can be used as cached data. The only thing that will happen is an update to the persistence layer, '
             '(`data/cset.csv` as of 2022/03/18).'),

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    run(**kwargs_dict)


if __name__ == '__main__':
    cli()
