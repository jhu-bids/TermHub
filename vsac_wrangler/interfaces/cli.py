#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""
from argparse import ArgumentParser

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
        choices=['google-sheet', 'oids-txt'],
        default='oids-txt',
        help='If "google-sheet", this will fetch from a specific, hard-coded Google Sheet, and pull OIDs from a '
             'specific column in that sheet. If "oids-txt" it will pull a list of OIDs from "input/oids.txt".')
    parser.add_argument(
        '-o', '--output-structure',
        choices=['fhir', 'vsac', 'palantir-concept-set-tables', 'atlas'],
        default='vsac',
        help='Destination structure. This determines the specific fields, in some cases, internal structure of the '
             'data in those fields.')
    parser.add_argument(
        '-f', '--output-format',
        choices=['tabular/csv', 'json'],
        default='json',
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
    msg = 'For "palantir-concept-set-tables" output-structure, output-format "json" is not available. ' \
          'Try "tabular/csv" instead.'
    if kwargs.output_structure == 'palantir-concept-set-tables' and kwargs.output_format == 'json':
        raise RuntimeError(msg)
    msg = 'For "atlas" output-structure, output-format "tabular/csv" is not available. Try "json" instead.'
    if kwargs.output_structure == 'atlas' and kwargs.output_format == 'tabular/csv':
        raise RuntimeError(msg)

def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    validate_args(kwargs)
    run(
        input_source_type=kwargs.input_source_type,
        output_structure=kwargs.output_structure,
        output_format=kwargs.output_format,
        field_delimiter=kwargs.tabular_field_delimiter,
        intra_field_delimiter=kwargs.tabular_intra_field_delimiter,
        json_indent=kwargs.json_indent,
        use_cache=kwargs.use_cache)


if __name__ == '__main__':
    cli()
