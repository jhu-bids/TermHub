"""Initialize database

1. Initialize the database if it doesn't exist
2. Download CSV files from the enclave
3. Load the data from the CSV files into the database
"""
import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from sqlalchemy.engine.base import Connection

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(THIS_DIR).parent.parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.config import CONFIG
from backend.db.load import download_artefacts, indexes_and_derived_tables, initialize_test_schema, seed
from backend.db.utils import database_exists, run_sql, show_tables, get_db_connection, DB

SCHEMA = CONFIG['schema']

DDL_MANAGE = """CREATE TABLE IF NOT EXISTS public.manage (
                    key text not null,
                    value text);"""

DDL_COUNTS = """CREATE TABLE IF NOT EXISTS public.counts (
                    timestamp text not null,
                    date text,
                    schema text not null,
                    "table" text not null,
                    count integer not null,
                    delta integer not null);"""

DDL_COUNTS_RUNS = """CREATE TABLE IF NOT EXISTS public.counts_runs (
                        timestamp text not null,
                        date text,
                        schema text not null,
                        note text);"""

# fetch_audit: table schema
#   table: text; examples: code_sets | concept_set_container | concept_set_members | concept_set_version_item
#   primary_key: text; comma-delimited: this should store the value of the keys, e.g. codeset_id 12345, concept_id 5678
#     would be 12345,5678
#   status_initially: text; factor: success | fail-excessive-members fail-excessive-items | fail-0-members |
#   fail-unknown?
#   success_datetime: timestamp; initially null, used by code that updates the derived tables.
#   comment: text
# todo: change comment to text[]?
DDL_FETCH_AUDIT = """CREATE TABLE IF NOT EXISTS public.fetch_audit (
                        "table" text not null,
                        primary_key text not null,
                        status_initially text not null,
                        success_datetime timestamp with time zone,
                        comment text);"""

DDL_CSET_COMPARE = """CREATE TABLE IF NOT EXISTS public.codeset_comparison (
                        fetch_time text,
                        orig_codeset_id integer,
                        new_codeset_id integer,
                        rpt json
                        );"""

def create_database(con: Connection, schema: str):
    """Create the database"""
    print('Current tables: ')
    show_tables(con)
    if not database_exists(con, DB):
        # noinspection PyUnresolvedReferences
        con.connection.connection.set_isolation_level(0)
        run_sql(con, 'CREATE DATABASE ' + DB)
        # noinspection PyUnresolvedReferences
        con.connection.connection.set_isolation_level(1)
    with get_db_connection(schema='') as con2:
        run_sql(con2, DDL_MANAGE)
        run_sql(con2, DDL_COUNTS)
        run_sql(con2, DDL_COUNTS_RUNS)
        run_sql(con2, DDL_FETCH_AUDIT)
        run_sql(con2, DDL_CSET_COMPARE)
        run_sql(con, f'CREATE SCHEMA IF NOT EXISTS {schema};')


def initialize(
    clobber=False, replace_rule=None, schema: str = SCHEMA, local=False, create_db=False, download=True, download_force_if_exists=False,
    test_schema=True, test_schema_only=False, hours_threshold_for_updates=24, optimization_experiment=None
):
    """Initialize set up of DB

    :param local: If True, does this on local instead of production database."""
    with get_db_connection(local=local, schema=schema) as con:
        if test_schema_only:
            return initialize_test_schema(con, schema, local=local)
        if create_db:
            create_database(con, schema)
        if download:
            download_artefacts(force_download_if_exists=download_force_if_exists)

        run_sql(con, f"""CREATE SCHEMA IF NOT EXISTS {schema};""")

        seed(con, schema, clobber, replace_rule, hours_threshold_for_updates, local=local)

        if optimization_experiment == 'n3c_no_rxnorm':
            delete_rxnorm_extension_records(con)

        indexes_and_derived_tables(con, schema, local=local)  # , start_step=30)

        if test_schema:
            initialize_test_schema(con, schema, local=local)


def delete_rxnorm_extension_records(con: Connection):
    """Delete all concepts in the RxNorm Extension vocabulary
        This is for issue #514 and
        https://github.com/jhu-bids/TermHub/tree/perf-tests/frontend/tests#no-rxnorm-extension-codes"""
    run_sql(con, """
               SELECT concept_id
               INTO rxnorm_ext_concepts
               FROM concept
               WHERE vocabulary_id = 'RxNorm Extension'
            """)
    run_sql(con, """
               DELETE FROM concept_set_members
               WHERE concept_id IN (SELECT concept_id FROM rxnorm_ext_concepts)
            """)
    run_sql(con, """
               DELETE FROM concept_set_version_item
               WHERE concept_id IN (SELECT concept_id FROM rxnorm_ext_concepts)
            """)




def cli():
    """Command line interface"""
    parser = ArgumentParser(description='Initializes DB.')
    parser.add_argument(
        '-D', '--clobber', action='store_true', default=False, help='If table exists, delete rows before seeding?')
    parser.add_argument(
        '-s', '--schema', default=SCHEMA, help='Name of the PostgreSQL schema to create to store tables.')
    parser.add_argument(
        '-l', '--local', action='store_true', default=False,
        help='Use local database? If this is set, will use DB related environmental variables that end with _LOCAL.')
    parser.add_argument(
        '-c', '--create-db', action='store_true', default=False,
        help='Create the database "termhub", Postgres schemas (e.g. "n3c" and "test_n3c") and auxiliary tables?')
    parser.add_argument(
        '-d', '--download', action='store_true', default=False,
        help='Download datasets necessary for seeding DB? Not needed if they\'ve already been downloaded.')
    parser.add_argument(
        '-f', '--download-force-if-exists', action='store_true', default=False,
        help='Force overwrite of existing dataset files?')
    parser.add_argument(
        '-T', '--test-schema-only', action='store_true', default=False,
        help='Skip main downloads and main schema, and just initialize the test schema. Will fail if main schema has '
             'never been initialized.')
    parser.add_argument(
        '-t', '--hours-threshold-for-updates', default=24,
        help='Threshold for how many hours since last update before we require refreshes. If last update time was less '
             'than this, nothing will happen. Will evaluate this separately for downloads of local artefacts as well '
             'as uploading data to the DB.\n'
             'This is useful if expecting errors to happen during table creation / seeding process, and you don\'t want'
             ' to start over from the beginning.')
    initialize(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
    # initialize(clobber=True, schema='n3c', download=False, test_schema=False) #, download_force_if_exists=True,  replace_rule='finish aborted upload',
    # schema = 'n3c'
    # con = get_db_connection(schema='n3c')
    # seed(con, schema, replace_rule='finish aborted upload', dataset_tables=['concept_ancestor'])
    # initialize(download=False, optimization_experiment='n3c_no_rxnorm', test_schema=False) # download_force_if_exists=True
    # initialize(schema='n3c_no_rxnorm', download=False, optimization_experiment='n3c_no_rxnorm', test_schema=False) # download_force_if_exists=True
