"""Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new,
resulting in initial fetch of concept set members being 0.

TODO: if every expression is set to `isExcluded=true`, we expect no members. Can add as a check rather than wait 2hrs"""
import os
import sys
import time
from argparse import ArgumentParser
from datetime import datetime
from typing import Dict, List, Set, Tuple

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, "..")
PROJECT_ROOT = os.path.join(BACKEND_DIR, "..")
sys.path.insert(0, str(PROJECT_ROOT))
from backend.utils import call_github_action
from enclave_wrangler.objects_api import concept_set_members__from_csets_and_members_to_db, \
    fetch_cset_and_member_objects
from backend.db.utils import SCHEMA, fetch_status_set_success, get_db_connection, reset_temp_refresh_tables, \
    select_failed_fetches, refresh_derived_tables

DESC = "Resolve any failures resulting from fetching data from the Enclave's objects API."


def _report_success(
    cset_ids: List[int], fetch_audit_row_lookup: Dict[str, Dict], comment_addition: str = None, use_local_db=False
):
    """Report success for a list of concept set IDs.
    todo: kind of weird to pass a lookup. Maybe do that beforehand and pass row dict"""
    success_rows = []
    for cset_id in cset_ids:
        row = fetch_audit_row_lookup[str(cset_id)]
        if comment_addition:
            row['comment'] = row['comment'] + '; ' + comment_addition
        success_rows.append(row)
    fetch_status_set_success(success_rows, use_local_db)


def resolve_failures_0_members_if_exist(use_local_db=False, via_github_action=True):
    """Starts handling of fetch failurers if they exist. Applies only to schema SCHEMA."""
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failures_exist: bool = any([int(x['primary_key']) for x in failures if x['status_initially'] == 'fail-0-members'])
    if failures_exist and via_github_action:
        call_github_action('resolve_fetch_failures_0_members.yml')
    elif failures_exist:
        resolve_fetch_failures_0_members(use_local_db=use_local_db)


def get_failures_0_members(version_id: int = None, use_local_db=False) -> Tuple[Set[int], Dict[str, Dict]]:
    """Gets list of IDs of failed concetp set versions as well as a lookup for more information about them"""
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failure_lookup: Dict[str, Dict] = {x['primary_key']: x for x in failures}
    failed_cset_ids: List[int] = [version_id] if version_id else [
        int(x['primary_key']) for x in failures if x['status_initially'] == 'fail-0-members']
    failed_cset_ids: Set[int] = set(failed_cset_ids)  # dedupe
    return failed_cset_ids, failure_lookup


def resolve_fetch_failures_0_members(
    version_id: int = None, use_local_db=False, polling_interval_seconds=30, schema=SCHEMA, runtime=2 * 60 * 60,
    loop=False
):
    """Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new
    resulting in initial fetch of concept set members being 0.
    :param version_id: Optional concept set version ID to resolve. If not provided, will check database for flagged
    failures.
    :param runtime: 2 hours
    :param loop: If True, will run in a loop to keep attempting to fetch. If this is set to False, it's probably
    because the normal DB refresh rate is already high, and this action runs at the end of every refresh (if there are
    any outstanding issus), so it's not really necessary to run these two concurrently.
    todo: Performance: Fetch only members, ideally: Even though we are fetching 'members', adding to the cset members
     table requires cset version and container metadata, and the function that does this expects them to be formaatted
     as objects, not as they come from our DB. We can fetch from DB and then convert to objects, but a lot of work for
     small performance gain."""
    print("Resolving fetch failures: ostensibly new (possibly draft) concept sets with >0 expressions but 0 members")
    # Collect failures
    failed_cset_ids, failure_lookup = get_failures_0_members(version_id, use_local_db)
    if not failed_cset_ids:
        print("No failures to resolve.")
        return

    # Resolve
    i = 0
    t0 = datetime.now()
    cset_is_draft_map: Dict[int, bool] = {}
    print(f"Fetching concept set versions and their related objects: {', '.join([str(x) for x in failed_cset_ids])}")
    while len(failed_cset_ids) > 0 and (datetime.now() - t0).total_seconds() < runtime:
        i += 1
        print(f"- attempt {i}: fetching members for {len(failed_cset_ids)} concept set versions")
        # Check for new failures: that may have occurred during runtime
        failed_cset_ids, failure_lookup_i = get_failures_0_members(version_id, use_local_db)
        failure_lookup.update(failure_lookup_i)
        # Fetch data
        csets_and_members: Dict[str, List[Dict]] = fetch_cset_and_member_objects(
            codeset_ids=list(failed_cset_ids), flag_issues=False)
        # - filter success & track results
        csets_and_members['OMOPConceptSet'] = [
            x for x in csets_and_members['OMOPConceptSet'] if x['member_items']]
        cset_is_draft_map.update({x['properties']['codesetId']: x['properties']['isDraft'] for x in csets_and_members['OMOPConceptSet']})
        success_cases: List[int] = [
            x['properties']['codesetId'] for x in csets_and_members['OMOPConceptSet']]
        failed_cset_ids = list(set(failed_cset_ids) - set(success_cases))

        # Update DB & report success
        if success_cases:
            try:
                with get_db_connection(schema=schema, local=use_local_db) as con:
                    concept_set_members__from_csets_and_members_to_db(con, csets_and_members)
                    refresh_derived_tables(con)
                print(f"Successfully fetched concept set members for concept set versions: "
                      f"{', '.join([str(x) for x in success_cases])}")
                _report_success(success_cases, failure_lookup, 'Success result: Found members', use_local_db)
            except Exception as err:
                reset_temp_refresh_tables(schema)
                raise err

        # Sleep or exit
        if not loop:
            break
        time.sleep(polling_interval_seconds)

    # Remove drafts from failures (as csets don't have members until drafts are finalized)
    failed_cset_ids = [cset_id for cset_id in failed_cset_ids if cset_is_draft_map[cset_id]]

    # Close out
    if failed_cset_ids and loop:
        print(f"2 hours have passed. No members were fetched for the following concept sets, but given the length "
              f"of time passed, members should have been available by now, and we assume that these concept sets do"
              f" not actually have members. Reporting resolved: {', '.join([str(x) for x in failed_cset_ids])}")
        comment = 'Success result: No members after 2 hours. Considering resolved.'
        _report_success(failed_cset_ids, failure_lookup, comment, use_local_db)
    elif failed_cset_ids:
        raise RuntimeError('Attempted to resolve fetch failures for the following concept sets, but was not able to do '
                           'so. It may be that the Enclave simply has not expanded their members yet.:\n\n'
                           f'{", ".join([str(x) for x in failed_cset_ids])}')
    else:
        print("All failures resolved.")


def cli():
    """Command line interface"""
    parser = ArgumentParser(prog="Resolve fetch failures.", description=DESC)
    parser.add_argument(
        "-l",
        "--use-local-db",
        action="store_true",
        default=False,
        required=False,
        help="Use local database instead of server.")
    parser.add_argument(
        "-v",
        "--version-id",
        type=int,
        required=False,
        help="Optional concept set version ID to resolve. If not provided, will check database for flagged failures.")
    parser.add_argument(
        "-i",
        "--polling-interval-seconds",
        required=False,
        default=30,
        help="How often, in seconds, to try to fetch again if fetching still yields 0 members.")
    resolve_fetch_failures_0_members(**vars(parser.parse_args()))


if __name__ == "__main__":
    cli()
