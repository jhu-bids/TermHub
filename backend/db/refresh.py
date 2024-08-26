"""DB Refresh: Refresh TermHub database w/ newest updates from the Enclave using the objects API."""
import dateutil.parser as dp
import os
import sys
from argparse import ArgumentParser
from datetime import datetime, timedelta
from typing import List, Union

import pytz
from sqlalchemy import Connection

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.analysis import counts_update, counts_docs
from backend.db.config import CONFIG
from backend.db.resolve_fetch_failures_0_members import resolve_failures_0_members_if_exist, \
    resolve_failures_excess_items_if_exist
from backend.db.utils import current_datetime, get_db_connection, is_refresh_active, last_refresh_timestamp, \
    reset_temp_refresh_tables, tz_datetime_str, update_db_status_var, check_db_status_var, delete_db_status_var
from enclave_wrangler.objects_api import csets_and_members_enclave_to_db

DESC = 'Refresh TermHub database w/ newest updates from the Enclave using the objects API.'
ERR_SINCE = '--since is more recent than the database\'s record of last refresh, which will result in missing data.'
HELP_SINCE = """A timestamp by which new data should be fetched. If not present, will look up the last time the DB was 
refreshed and fetch new data from that time. Valid formats: 
- Simple date timestamp, YYYY-MM-DD, e.g. 2022-02-22.
- ISO 8601 datetime with timezone offset, YYYY-MM-DDTHH:MM:SS.SSSSSS+HH:MM, e.g. 2022-02-22T22:22:22.222222+00:00."""
DEFAULT_BUFFER_HOURS = 0


def trigger_resolve_failures(
    resolve_fetch_failures_excess_items=False, resolve_fetch_failures_0_members=True, local=False
):
    """Trigger the GitHub actions to resolve fetch failures

    todo: very minor edge case to add: resolve_fetch_failures_excess_members"""
    # Routine: Check for and resolve any open fetch failures
    if resolve_fetch_failures_excess_items:
        resolve_failures_excess_items_if_exist(local)
    if resolve_fetch_failures_0_members:
        resolve_failures_0_members_if_exist(local)

def _calc_refresh_datetime(
    con: Connection, since: str, buffer_hours=DEFAULT_BUFFER_HOURS, force_non_contiguity=False
) -> str:
    """Calculate the datetime from which to fetch data since."""
    # Is 'since' a datetime or a date?
    since_is_datetime = since and 'T' in since

    # Validate: datetime formatting
    if since_is_datetime and not any(['+' in since, '-' in since]):
        raise ValueError('Invalid "since" param: Datetime used, but timezone offset was not included. See '
                         f'reference docs: \n\n{HELP_SINCE}')

    # Add buffer && reformat if simple date
    if since and since_is_datetime:
        since = str(dp.parse(since) - timedelta(hours=buffer_hours)).replace(' ', 'T')
    elif since and not since_is_datetime:
        since = str((dp.parse(since) - timedelta(hours=buffer_hours)).astimezone(pytz.utc)).replace(' ', 'T')

    # Validate: 'since' not more recent than last refresh
    last_refresh = last_refresh_timestamp(con)
    if since and dp.parse(since) > dp.parse(last_refresh) and not force_non_contiguity:
        raise ValueError(ERR_SINCE)

    # Format if necessary & return
    since = since if since else str(dp.parse(last_refresh) - timedelta(hours=buffer_hours)).replace(' ', 'T')
    return since


# todo: low priority: track the time it takes for this process to run, and then update the `manage` table, 2 variables:
#  total time for downloads, and total time for uploading to db (perhaps for each table as well)
# todo: store runs of db refresh in a table, so can have a reference for troubleshooting. e.g. date of run, and what
#  timestamp it fetched from.
# todo: What if 'since' is passed, but it is not the same date or before 'last_updated' in db? should print warning
def refresh_db(
    since: Union[datetime, str] = None, cset_ids: List[int] = None, use_local_db=False,  schema: str = CONFIG['schema'],
    force_non_contiguity=False, buffer_hours=DEFAULT_BUFFER_HOURS, resolve_fetch_failures_0_members=True,
    resolve_fetch_failures_excess_items=False,
):
    """Refresh the database

    :param: buffer_hours: An additional period of time before 'since' to fetch additional data, as a failsafe measure in
     case of possible API unreliability.
    :param force_non_contiguity: Used with `since`. If `since` timestamp is more recent than the database\'s record of
    when the last refresh occurred, this will result in there being a gap in which any changes that occurred during that
    time will not be fetched, resulting in an incomplete database. Therefore by default this will raise an error unless
    this is set to True.
    todo: resolve_fetch_failures_excess_items currently set to False until the following issues are addressed:
     - https://github.com/jhu-bids/TermHub/issues/499
     - https://github.com/jhu-bids/TermHub/issues/518
    todo: Can update update_db_status_var() so that it can accept optional param 'con' to improve performance.
    todo: refactor `new_request_while_refreshing` usage for brevity in code and DB: Rather than checking a variable
     new_request_while_refreshing , at the end of the refresh, if the last_refresh_request has changed / is newer than
     what was set at the beginning of the script, it knows that a new request while refreshing has occurred, and use
     that information to know to start new refresh. https://github.com/jhu-bids/TermHub/pull/469#discussion_r1253581138
    """
    local = use_local_db
    print('INFO: Starting database refresh.', flush=True)  # flush: for gh action

    # Validation
    if since and cset_ids:
        raise NotImplementedError('Cannot pass both "since" and "cset_ids" params.')

    # Calculate: Start & end time
    # end_time: Even though in reality the refresh will not end 1 microsecond after the start time, we're setting it
    # this way because this is the easiest way to make sure that future refreshes will not miss any new data that was
    # added between when the refresh started and ended.
    t0, start_time = datetime.now(), current_datetime()
    end_time_reported: str = tz_datetime_str(dp.parse(start_time) + timedelta(microseconds=1))

    if is_refresh_active():
        print('INFO: Refresh already in progress. When that process completes, it will restart again. Exiting.')
        update_db_status_var('new_request_while_refreshing', start_time, local)
        # todo: consider running trigger_resolve_failure(), but maybe not necessary.
        # trigger_resolve_failures(resolve_fetch_failures_excess_items, resolve_fetch_failures_0_members, local)
        return
    update_db_status_var('refresh_status', 'active', local)
    update_db_status_var('last_refresh_request', start_time, local)

    try:
        with get_db_connection(local=local) as con:
            since: str = _calc_refresh_datetime(con, since, buffer_hours, force_non_contiguity)
            since = since if not cset_ids else None
            # todo: when ready, will use all_new_objects_enclave_to_db() instead of csets_and_members_enclave_to_db()
            # - csets_and_members_enclave_to_db(): Runs the refresh
            new_data: bool = csets_and_members_enclave_to_db(con, since, cset_ids, schema)
        update_db_status_var('last_refresh_success', end_time_reported, local)
        update_db_status_var('last_refresh_result', 'success', local)
    except Exception as err:
        update_db_status_var('last_refresh_result', 'error', local)
        update_db_status_var('last_refresh_error_message', str(err), local)
        reset_temp_refresh_tables(schema)
        print(f"Database refresh incomplete; exception occurred.", file=sys.stderr)
        counts_update('DB refresh error.', schema, local, filter_temp_refresh_tables=True)
        print('Updating database counts. This could take a while...')
        counts_docs()
        raise err
    finally:
        # Update status vars
        update_db_status_var('last_refresh_exited', current_datetime(), local)
        update_db_status_var('refresh_status', 'inactive', local)
        trigger_resolve_failures(resolve_fetch_failures_excess_items, resolve_fetch_failures_0_members, local)

    if new_data:
        print('DB refresh complete.')
        print('Updating database counts. This could take a while...')
        counts_update('DB refresh.', schema, local)
        counts_docs()
        print(f'INFO: Database refresh complete in {(datetime.now() - t0).seconds} seconds.')
    else:
        print('INFO: No new data was found in the Enclave. Exiting.')

    if check_db_status_var('new_request_while_refreshing'):
        print('INFO: New refresh request detected while refresh was running. Starting a new refresh.')
        delete_db_status_var('new_request_while_refreshing')
        refresh_db(None, None, use_local_db, schema, force_non_contiguity)


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog='DB Refresh', description=DESC)
    parser.add_argument(
        '-l', '--use-local-db', action='store_true', default=False, required=False,
        help='Use local database instead of server.')
    parser.add_argument(    # changing buffer hours to 2 so don't miss cset members
        '-b', '--buffer-hours', default=DEFAULT_BUFFER_HOURS, required=False,
        help='An additional period of time before "since" to fetch additional data, as a failsafe measure in case of '
             'possible API unreliability. Somewhat redundant with fetch_failures_0_members process.')
    parser.add_argument('-s', '--since', required=False, help=HELP_SINCE)
    parser.add_argument("-c", "--cset-ids", type=int, required=False, nargs='+',
        help="Run just for certain code sets. Pass their IDs space-delimited, e.g. --cset-ids 123 456. Should only be"
             " passed without 'since'.")
    refresh_db(**vars(parser.parse_args()))


if __name__ == '__main__':
    cli()
