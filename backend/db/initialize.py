"""Initialize database

1. Initialize the database if it doesn't exist
2. Download CSV files from the enclave
3. Load the data from the CSV files into the database
"""
import os
import sys
from pathlib import Path

from sqlalchemy.engine.base import Connection

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(THIS_DIR).parent.parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.config import CONFIG
from backend.db.load import download_artefacts, indexes_and_derived_tables, seed
from backend.db.utils import database_exists, run_sql, show_tables, get_db_connection, DB

SCHEMA = CONFIG['schema']


def create_db(con: Connection):
    """Create the database"""
    if CONFIG["server"] == 'postgresql':  # postgres doesn't have create database if not exists
        show_tables(con)
        if not database_exists(con, DB):
            # noinspection PyUnresolvedReferences
            con.connection.connection.set_isolation_level(0)
            run_sql(con, 'CREATE DATABASE ' + DB)
            # noinspection PyUnresolvedReferences
            con.connection.connection.set_isolation_level(1)
    else:
        run_sql(con, 'CREATE DATABASE IF NOT EXISTS ' + DB)
        run_sql(con, f'USE {DB}')
    with get_db_connection(schema='') as con2:
        run_sql(con2, "CREATE TABLE IF NOT EXISTS public.manage (key text not null, value text);")


def initialize(
    clobber=False, schema: str = SCHEMA, local=False, _create_db=False, download=True,
    download_force_if_exists=False
):
    """Initialize set up of DB

    :param local: If True, does this on local instead of production database.

    Resources
    - https://docs.sqlalchemy.org/en/20/core/engines.html
    - https://docs.sqlalchemy.org/en/20/dialects/mysql.html
    """
    with get_db_connection(local=local) as con:
        if _create_db:
            create_db(con)  # causing error. don't need it at the moment anyway
        if download:
            download_artefacts(force_download_if_exists=download_force_if_exists)
        seed(con, schema, clobber)
        indexes_and_derived_tables(con, schema) #, start_step=30)


if __name__ == '__main__':
    initialize()
