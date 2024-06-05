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

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, "..")
PROJECT_ROOT = os.path.join(BACKEND_DIR, "..")
sys.path.insert(0, str(PROJECT_ROOT))
from backend.utils import call_github_action
from backend.db.resolve_fetch_failures_excess_items import resolve_fetch_failures_excess_items
from backend.db.utils import SCHEMA, fetch_status_set_success, get_db_connection, reset_temp_refresh_tables, \
    select_failed_fetches, refresh_derived_tables, sql_in, sql_query
from enclave_wrangler.objects_api import concept_set_members__from_csets_and_members_to_db, \
    fetch_cset_and_member_objects, get_csets_over_threshold

DESC = "Resolve any failures resulting from fetching data from the Enclave's objects API."


def _report_success(
    cset_ids: List[int], fetch_audit_row_lookup: Dict[int, Dict], comment_addition: str = None, use_local_db=False
):
    """Report success for a list of concept set IDs.
    todo: kind of weird to pass a lookup. Maybe do that beforehand and pass row dict"""
    success_rows = []
    for cset_id in cset_ids:
        row = fetch_audit_row_lookup[cset_id]
        if comment_addition:
            row['comment'] = row['comment'] + '; ' + \
            'Success result: ' if not comment_addition.startswith('Success result: ') else '' + comment_addition
        success_rows.append(row)
    fetch_status_set_success(success_rows, use_local_db)


def resolve_failures_excess_members_if_exist():
    """Starts handling of fetch failurers if they exist. Applies only to schema SCHEMA.

    todo: implement this very rare edge case. There may have only been 1 case in all of enclave existence"""
    return NotImplementedError


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

def filter_cset_id_where_0_expanded_members(cset_ids: List[int], schema=SCHEMA, use_local_db=False) -> List[int]:
    """Filter cset IDs where there are 0 members when expanded

    TODO: complex cases: presently only does simple case: isExcluded=true, includeDescendants=false,
     includeMapped=false. Ideally we'd also check cases where isExcluded=true, but if any includeDescendants=true,
     check concept_ancestor to see if there actually are any descendants, and for includeMapped=true, check
     concept_relationship to see if any mapped."""
    qry = f"""SELECT codeset_id
        FROM concept_set_version_item AS csvi
        WHERE codeset_id {sql_in(cset_ids)}
        GROUP BY codeset_id
        HAVING COUNT(*) = COUNT(
          CASE WHEN "isExcluded" = true AND "includeDescendants" = false AND "includeMapped" = false
          THEN 1 ELSE NULL END);"""
    with get_db_connection(schema=schema, local=use_local_db) as con:
        id_rows: List[List[float]] = sql_query(con, qry, return_with_keys=False)
        ids: List[int] = [int(x[0]) for x in id_rows]
        return ids


def get_failures_0_members(
    version_id: Union[int, List[int]] = None, use_local_db=False
) -> Tuple[Set[int], Dict[int, Dict]]:
    """Gets list of IDs of failed concetp set versions as well as a lookup for more information about them"""
    # Typing modification
    version_id: List[int] = [version_id] if version_id and not isinstance(version_id, list) else version_id

    # Lookup failure data in DB
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failure_lookup: Dict[int, Dict] = {int(x['primary_key']): x for x in failures}
    failure_cset_ids: Set[int] = set(version_id if version_id else [
        int(x['primary_key']) for x in failures if x['status_initially'] == 'fail-0-members'])

    # Validate & filter
    non_failures_passed: Set[int] = set(version_id).difference(failure_lookup.keys()) if version_id else set()
    if bool(version_id and non_failures_passed):
        print("Warning: Cset IDs were passed to be resolved, but these are no longer failures; skipping them: "
              f"{', '.join([str(x) for x in non_failures_passed])}", file=sys.stderr)
    failure_cset_ids = failure_cset_ids - non_failures_passed

    return failure_cset_ids, failure_lookup


def resolve_fetch_failures_0_members(
    version_id: int = None, use_local_db=False, polling_interval_seconds=30, schema=SCHEMA,
    expansion_threshold_seconds=2 * 60 * 60, loop=False
):
    """Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new
    resulting in initial fetch of concept set members being 0.
    :param version_id: Optional concept set version ID to resolve. If not provided, will check database for flagged
    failures.
    :param expansion_threshold_seconds: The length of time that we reasonably expect that the Enclave should take to expand
    :param loop: If True, will run in a loop to keep attempting to fetch. If this is set to False, it's probably
    because the normal DB refresh rate is already high, and this action runs at the end of every refresh (if there are
    any outstanding issus), so it's not really necessary to run these two concurrently.
    todo: version_id: support list of IDs (comma-delimited)
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
    while len(failed_cset_ids) > 0 and (datetime.now() - t0).total_seconds() < expansion_threshold_seconds:
        i += 1
        if loop:
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
            print(f"Discarded drafts detected; marking resolved: {', '.join([str(x) for x in discarded_cset_ids])}")
            _report_success(list(discarded_cset_ids), failure_lookup, 'Discarded draft', use_local_db)

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
                _report_success(success_cset_ids, failure_lookup, 'Found members', use_local_db)
            except Exception as err:
                reset_temp_refresh_tables(schema)
                raise err

        # Sleep or exit
        if not loop:
            break
        time.sleep(polling_interval_seconds)

    # Csets with 0 expansion members
    #  - todo: only detecting simple cases. For more info, see docstring of filter_cset_id_where_0_expanded_members()
    csets_w_no_expanded_members: List[int] = filter_cset_id_where_0_expanded_members(failed_cset_ids)
    if csets_w_no_expanded_members:
        comment = 'There are 0 expansion members because 100% of the expressions are set to isExcluded=true, ' + \
            'includeDescendants=false, and includeMapped=false.'
        print(f'Csets detected matching the following condition; marking them resolved:\n'
              f'- Condition: {comment}\n'
              f'- Cset IDs:', f'{", ".join([str(x) for x in csets_w_no_expanded_members])}')
        _report_success(csets_w_no_expanded_members, failure_lookup, comment, use_local_db)
        failed_cset_ids = list(set(failed_cset_ids) - set(csets_w_no_expanded_members))

    # Parse drafts from actual failures
    still_draft_cset_ids: Set[int] = set([cset_id for cset_id in failed_cset_ids if cset_is_draft_map[cset_id]])
    if still_draft_cset_ids:
        print(f"Fetch attempted for the following csets, but they still remain drafts and thus still have not had their"
              f" members expanded yet: {', '.join([str(x) for x in still_draft_cset_ids])}")
    non_draft_failure_ids: Set[int] = set(failed_cset_ids) - still_draft_cset_ids

    # Filter by only if has been finalized longer than we would expect it should take for expansion to be available
    # noinspection PyUnboundLocalVariable
    still_draft_csets: List[Dict] = [
        x['properties'] for x in csets_and_members['OMOPConceptSet']
        if x['properties']['codesetId'] in non_draft_failure_ids]
    expansion_threshold_minutes = int(expansion_threshold_seconds / 60)
    final_failure_ids: Set[int] = get_csets_over_threshold(still_draft_csets, expansion_threshold_minutes)

    # Close out
    if final_failure_ids and loop:
        # todo: maybe this is not optimal. Maybe what we should do is check all the expression items and see if 100% are
        #  cases of isExcluded=true and includeDescendants=false. This should be the only case in which a cset is
        #  finalized and has 0 members.
        print(f"2 hours have passed. No members were fetched for the following concept sets, but given the length "
              f"of time passed, members should have been available by now, and we assume that these concept sets do"
              f" not actually have members. Reporting resolved: {', '.join([str(x) for x in final_failure_ids])}")
        comment = 'No members after 2 hours. Considering resolved.'
        _report_success(list(final_failure_ids), failure_lookup, comment, use_local_db)
    elif final_failure_ids:
        # todo: for troubleshooting, it would help to print the timestamp of when the cset was created here, as well as
        #  its age (in minutes). For the latter, would involve passing arg return_type='csets_by_id' to
        #  get_csets_over_threshold().
        raise RuntimeError(
            'Attempted to resolve fetch failures for the following concept sets, but was not able to do so. The cset '
            f'has been finalized, and it has been over our threshold of {expansion_threshold_minutes} minutes since the'
            f' cset was created, so we would have typically the expansion would\'ve happened by now if it was '
            f'finalized when or soon after it was created, but sometimes it takes longer, or perhaps the cset was not'
            f' finalized very soon after it was created; the expansion may still be pending. Failed IDs:\n\n'
            f'{", ".join([str(x) for x in final_failure_ids])}')
    else:
        print("Complete: All outstanding non-draft failures resolved.")


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
