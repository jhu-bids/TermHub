#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
import ArgumentParser
from argparse import ArgumentParser
from typing import Dict

from enclave_wrangler.main import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for working w/ the Palantir Foundry enclave API.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-i', '--input-csv-folder-path',
        help='Path to folder with 3 files that have specific columns that adhere to concept table data model. These '
             'files must have the following names: i. code_sets.csv, ii. concept_set_container_edited.csv, iii. '
             'concept_set_version_item_rv_edited.csv')

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
