#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
from argparse import ArgumentParser
from sys import stderr

from value_set_vsac_to_json.definitions.error import PackageException
from value_set_vsac_to_json.main import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for converting VSAC value sets into various formats.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-f', '--format',
        choices=['fhir', 'omop'],
        default='omop',
        help='Destination format to transform VSAC value set into')

    parser.add_argument(
        '-a', '--artefact',
        choices=['csv_fields', 'json', 'tsv_code'],
        default='json',
        help='The kind of output artefact to create')

    # out_help = ('Path to save output file. If not present, same directory of'
    #             'any input files passed will be used.')
    # parser.add_argument('-o', '--outpath', help=out_help)

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program.

    Command Syntax:

    Examples:

    """
    parser = get_parser()
    kwargs = parser.parse_args()

    try:
        run(format=kwargs.format)
    except PackageException as err:
        err = 'An error occurred.\n\n' + str(err)
        print(err, file=stderr)


if __name__ == '__main__':
    cli()
