#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
# TODO: For some reason, 'argparse' is not available in Stephanie's Python3.9 standard library, so she has installed
#  the "ArgumentParser" class manually. However, we really want everyone to be using the same libraries, so
#  we need to find out why this is happening to her, and fix it, instead of the workaround below: - Joe 2022/02/02
try:
    #import ArgumentParser
    from argparse import ArgumentParser
except ModuleNotFoundError:
    from argparse import ArgumentParser
from typing import Dict

from vsac_wrangler.main import run


def get_parser():
    """Add required fields to parser.

    Returns:
        ArgumentParser: Argeparse object.
    """
    package_description = 'Tool for converting VSAC value sets into various formats.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-i', '--input-source-type',
        choices=['google-sheet', 'txt', 'csv'],
        default='csv',
        help='If (a) "google-sheet", this will fetch from a specific, hard-coded GoogleSheet URL, and pull OIDs from a '
             'specific hard-codeed column in that sheet. You may also want to specify the `--google-sheet-name`. If (b)'
             ' "txt", or (c) "csv", please supply an `--input-path`. In case of "txt", it is expected that each '
             'line of the file contains an OID and nothing else. In case of "csv", it is expected that there be an '
             '"oid" column.')
    parser.add_argument(
        '-p', '--input-path', required=False,
        help='Path to input file. Required if `--input-source-type` is "txt" or "csv".')
    # to-do: Add Google Sheet URL
    parser.add_argument(
        '-g', '--google-sheet-name',
        choices=['CDC reference table list', 'Lisa1 VSAC', 'Lisa2 VSAC GRAVITY'],
        default='CDC reference table list',
        help='The name of the tab within a the GoogleSheet containing the target data within OID column. Make sure to '
             'encapsulate the text in quotes, e.g. `-g "Lisa1 VSAC"`. This option can only be used if '
             '`--input-source-type` is `google-sheet`.')
    parser.add_argument(
        '-o', '--output-structure',
        choices=['fhir', 'vsac', 'palantir-concept-set-tables', 'atlas', 'normalized'],
        default='vsac',
        help='Destination structure. This determines the specific fields, in some cases, internal structure of the '
             'data in those fields. About structures: (a) "fhir" is intended to be uploaded to a FHIR server, (b) '
             '"vsac" retains similar struture/fields as VSAC data model, (c) "palantir-concept-set-tables" produces'
             'CSV files that can be bulk uploaded / appended in the N3C Palantir Foundry data enclave, (d) "atlas" '
             'produces a JSON format adherent to the Atlas DB data model, and (e) "normalized" creates a data structure'
             'that is normalized as much as possible, containing minimal amount of information / structure needed.')
    parser.add_argument(
        '-f', '--output-format',
        choices=['tabular/csv', 'json'],
        default='tabular/csv',
        required=True,
        help='The output format. If csv/tabular, it will produce a tabular file; CSV by default. This can be changed '
             'to TSV by passing "\t" as the field-delimiter.')
    parser.add_argument(
        '-d', '--tabular-field-delimiter',
        choices=[',', '\t'],
        default=',',
        help='Field delimiter for tabular output. This applies when selecting "tabular/csv" for "output-format". By '
             'default, uses ",", which menas that the output will be CSV (Comma-Separated Values). If "\t" is chosen, '
             'output will be TSV (Tab-Separated Values).')
    parser.add_argument(
        '-d2', '--tabular-intra-field-delimiter',
        choices=[',', '\t', ';', '|'],
        default='|',
        help='Intra-field delimiter for tabular output. This applies when selecting "tabular/csv" for "output-format". '
             'This delimiter will be used when a specific field contains multiple values. For example, in "tabular/csv"'
             ' format, there will be 1 row per combination of OID (Object ID) + code system. A single OID represents '
             'a single value set, which can have codes from multiple code systems. For a given OID+CodeSystem combo, '
             'there will likely be multiple codes in the "code" field. These codes will be delimited using the '
             '"intra-field delimiter".')
    parser.add_argument(
        '-j', '--json-indent',
        default=4,
        help='The number of spaces to indent when outputting JSON. If 0, there will not only be no indent, but there '
             'will also be no whitespace. 0 is useful for minimal file size. 2 and 4 tend to be  standard indent values'
             ' for readability.')
    parser.add_argument(
        '-c', '--use-cache',
        action='store_true',
        help='When running this tool, a cache of the results from the VSAC API will always be saved. If this flag is '
             'passed, the cached results will be used instead of calling the API. This is useful for (i) working '
             'offline, or (ii) speeding up processing. In order to not use the cache and get the most up-to-date '
             'results (both from (i) the OIDs present in the Google Sheet, and (ii) results from VSAC), simply run the'
             ' tool without this flag.'),

    return parser


def validate_args(kwargs):
    """Validate CLI args"""
    msg = 'Must select different delimiters for "tabular field delimiter" and "tabular intra-field delimiter".'
    if kwargs.tabular_field_delimiter == kwargs.tabular_intra_field_delimiter:
        raise RuntimeError(msg)
    msg = f'For "{kwargs.output_structure}" `--output-structure`, `--output-format` "json" is not available. ' \
          'Try "tabular/csv" instead.'
    if kwargs.output_structure in ['palantir-concept-set-tables', 'normalized'] and kwargs.output_format == 'json':
        raise RuntimeError(msg)
    msg = 'For "atlas" `--output-structure`, `--output-format` "tabular/csv" is not available. Try "json" instead.'
    if kwargs.output_structure == 'atlas' and kwargs.output_format == 'tabular/csv':
        raise RuntimeError(msg)
    msg = 'If `--input-source-type` is "txt" or "csv", `--input-path` is required.'
    if kwargs.input_source_type in ['txt', 'csv'] and not kwargs.input_path:
        raise RuntimeError(msg)
    # to-do: It would be ideal if we could show this error when the user /explicitly/ passes these arguments.
    # ...but unfortunately this error also shows even if the user passes no arguments at all, due to the default args.
    # msg = 'Can only pass google sheet name if input source is a google shet.'
    # if 'google_sheet_name' in kwargs and kwargs.input_source_type != 'google-sheet':
    #     raise RuntimeError(msg)


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    validate_args(kwargs)
    kwargs_dict: Dict = vars(kwargs)
    # TODO: this is probably better done a different way? This is a fix so that subfolder isn't created when not needed
    if kwargs_dict['input_source_type'] != 'google-sheet':
        del kwargs_dict['google_sheet_name']
    run(**kwargs_dict)


if __name__ == '__main__':
    cli()
