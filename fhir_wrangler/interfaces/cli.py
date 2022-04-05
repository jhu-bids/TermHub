#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
# TODO: For some reason, 'argparse' is not available in Stephanie's Python3.9 standard library, so she has installed
#  the "ArgumentParser" class manually. However, we really want everyone to be using the same libraries, so
#  we need to find out why this is happening to her, and fix it, instead of the workaround below: - Joe 2022/02/02
from typing import Dict

try:
    import ArgumentParser
except ModuleNotFoundError:
    from argparse import ArgumentParser

from fhir_wrangler.main import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'A FHIR client, mostly for BIDS / N3C DI&H / TIMS internal purposes.'
    parser = ArgumentParser(description=package_description)
    parser.add_argument(
        '-d', '--delete-nonauthoritative-value-sets', action='store_true',
        help="If this options is present, this tool will look at the`internal_id` / `dih_id` in `data/cset.csv` and "
             "delete any value sets with IDs not in this list. Note that in HAPI / FHIR, at least one non-numeric "
             "character is required for assigned IDs. We've handled this by prepending an 'a' before the integer IDs. "
             "This client has been programmed to account for this.")
    parser.add_argument(
        '-u', '--url', required=True, nargs='+',
        help='One or more URLs of ValueSet endpoint(s), e.g. http://localhost:8080/fhir/ValueSet). Repeat this flag as '
             'many times as needed, e.g. `-u <url1> -u <url2>.')

    return parser


def cli():
    """Command line interface for package.

    Side Effects: Executes program.

    Command Syntax:

    Examples:

    """
    parser = get_parser()
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    run(**kwargs_dict)


if __name__ == '__main__':
    cli()
