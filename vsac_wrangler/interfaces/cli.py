#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command Line Interface."""

from typing import Dict

from _cli import get_parser
from _cli import  validate_args
from vsac_wrangler.main import run

def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    parser = get_parser()
    kwargs = parser.parse_args()
    validate_args(kwargs)
    kwargs_dict: Dict = vars(kwargs)
    run(**kwargs_dict)

if __name__ == '__main__':
    cli()
