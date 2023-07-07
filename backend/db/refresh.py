"""DB Refresh: Refresh TermHub database w/ newest updates from the Enclave using the objects API."""
import os
import sys
from argparse import ArgumentParser

from datetime import datetime
from typing import Union
import dateutil.parser as dp

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.analysis import counts_update,counts_docs
from backend.db.config import CONFIG
from backend.db.utils import current_datetime, get_db_connection, last_refresh_timestamp, update_db_status_var,check_db_status_var, delete_db_status_var
from enclave_wrangler.objects_api import csets_and_members_enclave_to_db,is_new_db_data

DESC = 'Refresh TermHub database w/ newest updates from the Enclave using the objects API.'
SINCE_ERR = '--since is more recent than the database\'s record of last refresh, which will result in missing data.'


# todo: low priority: track the time it takes for this process to run, and then update the `manage` table, 2 variables:
#  total time for downloads, and total time for uploading to db (perhaps for each table as well)
# todo: store runs of db refresh in a table, so can have a reference for troubleshooting. e.g. date of run, and what
#  timestamp it fetched from.
# todo: What if 'since' is passed, but it is not the same date or before 'last_updated' in db? should print warning
def refresh_db(
    since: Union[datetime, str] = None, use_local_db=False,  schema: str = CONFIG['schema'],
    force_non_contiguity=False
):
    """Refresh the database

    :param force_non_contiguity: Used with `since`. If `since` timestamp is more recent than the database\'s record of
    when the last refresh occurred, this will result in there being a gap in which any changes that occurred during that
    time will not be fetched, resulting in an incomplete database. Therefore by default this will raise an error unless
    this is set to True.
    todo: Can update update_db_status_var() so that it can accept optional param 'con' to improve performance."""
    local = use_local_db
    print('INFO: Starting database refresh.', flush=True)  # flush: for gh action
    t0, t0_str = datetime.now(), current_datetime()

    with get_db_connection(local=local) as con:
        last_refresh = last_refresh_timestamp(con)
        if since and dp.parse(since) > dp.parse(last_refresh) and not force_non_contiguity:
            raise ValueError(SINCE_ERR)
        since = since if since else last_refresh

        #todo: new way of checking db is active
        '''if not is_new_db_data(since):
            'INFO: Database is up to date, no refresh necessary'
            return'''

        if check_db_status_var('refresh_status') == 'active':
            update_db_status_var('new_request_while_refreshing', t0_str, local)
            return

        print('INFO: Starting database refresh.', flush=True)  # flush: for gh action
        update_db_status_var('refresh_status', 'active', local)
        update_db_status_var('last_refresh_request', current_datetime(), local)
        try:
            # Refresh DB:
            # todo: will use instead when ready: all_new_objects_enclave_to_db()
            csets_and_members_enclave_to_db(con, schema, since)

            counts_update('DB refresh.', schema, local)
            update_db_status_var('refresh_status', 'inactive', local)
            update_db_status_var('last_refresh_success', current_datetime(), local)
            update_db_status_var('last_refresh_result', 'success', local)
            print(f'INFO: Database refresh complete in {(datetime.now() - t0).seconds} seconds.')

        except Exception as err:
            update_db_status_var('last_refresh_result', 'error', local)
            update_db_status_var('refresh_status', 'inactive', local)
            counts_update('DB refresh error.', schema, local, filter_temp_refresh_tables=True)
            print(f"Database refresh incomplete. An exception occurred.", file=sys.stderr)
            raise err

    if check_db_status_var('new_request_while_refreshing'):
        # possibly look at the timestamp for sanity check
        delete_db_status_var('new_request_while_refreshing')
        refresh_db(use_local_database=use_local_database)


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='DB Refresh', description=DESC)
    parser.add_argument(
        '-l', '--use-local-db', action='store_true', default=False, required=False,
        help='Use local database instead of server.')
    parser.add_argument(
        '-s', '--since', required=False,
        help='A timestamp by which new data should be fetched. If not present, will look up the last time the DB was '
             'refreshed and fetch new data from that time. Format: ISO 8601, with timezone offset, formatted as '
             'YYYY-MM-DDTHH:MM:SS.SSSSSS+HH:MM, e.g. 2022-02-22T22:22:22.222222+00:00.')

    refresh_db(**vars(parser.parse_args()))

if __name__ == '__main__':
    cli()
