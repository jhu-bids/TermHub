#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
from argparse import ArgumentParser
from sys import stderr

from value_set_csv_to_fhir_json.definitions.error import PackageException
from value_set_csv_to_fhir_json.fhir_value_set_csv_to_json import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for converting extensinoal value sets in CSV ' \
        'format to JSON format able to be uploaded to a FHIR server.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument('-f', '--file-path', help='Path to CSV file')

    # arg2_help = 'Description'
    # parser.add_argument('-s', '--second-arg', nargs='+', help=arg2_help)

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
        run(file_path=kwargs.file_path)
    except PackageException as err:
        err = 'An error occurred.\n\n' + str(err)
        print(err, file=stderr)


if __name__ == '__main__':
    cli()
