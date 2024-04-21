"""Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new,
resulting in initial fetch of concept set members being 0.

TODO: if every expression is set to `isExcluded=true`, we expect no members. Can add as a check rather than wait 2hrs"""
import os
import sys
import time
from argparse import ArgumentParser
from copy import copy, deepcopy
from datetime import datetime
from typing import Dict, List, Set, Tuple, Union

from backend.db.resolve_fetch_failures_excess_items import resolve_fetch_failures_excess_items

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


#todo: could DRY up resolve_failures_excess_items_if_exist() and resolve_failures_0_members_if_exist(), especially
# if/when creating resolve_failures_excess_members_if_exist()
# - especially needs to be refactored because resolve_failures_excess_items_if_exist() doesn't belong in
#   resolve_failures_0_members.py
def resolve_failures_excess_items_if_exist(use_local_db=False, via_github_action=True):
    """Starts handling of fetch failurers if they exist. Applies only to schema SCHEMA."""
    failure_type = 'fail-excessive-items'
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failures_exist: bool = any(
        [int(x['primary_key']) for x in failures if x['status_initially'] == failure_type])
    if failures_exist:
        print(f"Fetch failures of type detected: {failure_type}\n - " +
              'Kicking off GitHub action to resolve.' if via_github_action else 'Attempting to resolve.')
        if via_github_action:
            call_github_action('resolve-fetch-failures-excess-items')
        else:
            resolve_fetch_failures_excess_items(use_local_db=use_local_db)


def resolve_failures_0_members_if_exist(use_local_db=False, via_github_action=True):
    """Starts handling of fetch failurers if they exist. Applies only to schema SCHEMA."""
    failure_type = 'fail-0-members'
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failures_exist: bool = any([int(x['primary_key']) for x in failures if x['status_initially'] == failure_type])
    if failures_exist:
        print(f"Fetch failures of type detected: {failure_type}\n - " +
              'Kicking off GitHub action to resolve.' if via_github_action else 'Attempting to resolve.')
        if via_github_action:
            call_github_action('resolve_fetch_failures_0_members.yml')
        else:
            resolve_fetch_failures_0_members(use_local_db=use_local_db)


def get_failures_0_members(version_id: Union[int, List[int]] = None, use_local_db=False) -> Tuple[Set[int], Dict[str, Dict]]:
    """Gets list of IDs of failed concetp set versions as well as a lookup for more information about them"""
    version_id: List[int] = [version_id] if version_id and isinstance(version_id, int) else version_id

    failures: List[Dict] = select_failed_fetches(use_local_db)
    failure_lookup: Dict[str, Dict] = {x['primary_key']: x for x in failures}
    failed_cset_ids: List[int] = version_id if version_id else [
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
    failed_cset_ids_prefilter, failure_lookup = get_failures_0_members(version_id, use_local_db)
    failed_cset_ids = copy(failed_cset_ids_prefilter)
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

        # - identify & report discarded drafts
        fetch_cset_ids: Set[int] = set([x['properties']['codesetId'] for x in csets_and_members['OMOPConceptSet']])
        discarded_cset_ids: Set[int] = failed_cset_ids - fetch_cset_ids
        if discarded_cset_ids:
            print(f"Discarded drafts detected: {', '.join([str(x) for x in discarded_cset_ids])}")
            _report_success(list(discarded_cset_ids), failure_lookup, 'Success result: Discarded draft', use_local_db)

        # - identify persistent, long-lived drafts
        cset_is_draft_map.update(
            {x['properties']['codesetId']: x['properties']['isDraft'] for x in csets_and_members['OMOPConceptSet']})
        # - identify / filter success cases & track results
        success_cases: Dict[str, List[Dict]] = deepcopy(csets_and_members)
        success_cases['OMOPConceptSet'] = [x for x in success_cases['OMOPConceptSet'] if x['member_items']]
        success_cset_ids: List[int] = [x['properties']['codesetId'] for x in success_cases['OMOPConceptSet']]
        failed_cset_ids = list(set(failed_cset_ids) - set(success_cset_ids) - set(discarded_cset_ids))

        # Update DB & report success
        if success_cset_ids:
            try:
                with get_db_connection(schema=schema, local=use_local_db) as con:
                    concept_set_members__from_csets_and_members_to_db(con, success_cases)
                    refresh_derived_tables(con)
                print(f"Successfully fetched concept set members for concept set versions: "
                      f"{', '.join([str(x) for x in success_cset_ids])}")
                _report_success(success_cset_ids, failure_lookup, 'Success result: Found members', use_local_db)
            except Exception as err:
                reset_temp_refresh_tables(schema)
                raise err

        # Sleep or exit
        if not loop:
            break
        time.sleep(polling_interval_seconds)

    # Parse drafts from actual failures
    still_draft_cset_ids: Set[int] = set([cset_id for cset_id in failed_cset_ids if cset_is_draft_map[cset_id]])
    if still_draft_cset_ids:
        print(f"Fetch attempted for the following csets, but they still remain drafts and thus still have not had their"
              f" members expanded yet: {', '.join([str(x) for x in still_draft_cset_ids])}")
    true_failed_cset_ids: Set[int] = set(failed_cset_ids) - still_draft_cset_ids

    # Close out
    if true_failed_cset_ids and loop:
        # todo: maybe this is not optimal. Maybe what we should do is check all the expression items and see if 100% are
        #  cases of isExcluded=true and includeDescendants=false. This should be the only case in which a cset is
        #  finalized and has 0 members.
        print(f"2 hours have passed. No members were fetched for the following concept sets, but given the length "
              f"of time passed, members should have been available by now, and we assume that these concept sets do"
              f" not actually have members. Reporting resolved: {', '.join([str(x) for x in failed_cset_ids])}")
        comment = 'Success result: No members after 2 hours. Considering resolved.'
        _report_success(failed_cset_ids, failure_lookup, comment, use_local_db)
    elif true_failed_cset_ids:
        raise RuntimeError('Attempted to resolve fetch failures for the following concept sets, but was not able to do '
                           'so. It may be that the Enclave simply has not expanded their members yet:\n\n'
                           f'{", ".join([str(x) for x in failed_cset_ids])}')
    else:
        print("All outstanding non-draft failures resolved.")


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
