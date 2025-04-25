"""Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new,
resulting in initial fetch of concept set members being 0.

todo's:
todo #1 Rare occasion: Ideally, if manually passing and using --force, it's because there was previouslya success,
 but this is being re-run for those cases because the success is in question. In these cases, ideally we'd figure out
 if any new / different data for the given cset was actually found / imported, and report about that in the comment. So
 for now, we filter: if manually passing IDs and using --force, won't be in lookup.
"""
import json
import os
import sys
import time
from argparse import ArgumentParser
from copy import copy, deepcopy
from datetime import datetime
from typing import Dict, List, Set, Tuple, Union

from sqlalchemy import Connection

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, "..")
PROJECT_ROOT = os.path.join(BACKEND_DIR, "..")
sys.path.insert(0, str(PROJECT_ROOT))
from backend.utils import call_github_action
from backend.db.resolve_fetch_failures_excess_items import resolve_fetch_failures_excess_items
from backend.db.utils import SCHEMA, fetch_status_set_success, get_db_connection, reset_temp_refresh_tables,\
    run_sql, select_failed_fetches, refresh_derived_tables, sql_in, sql_query
from enclave_wrangler.objects_api import csets_and_members_to_db, fetch_cset_and_member_objects, fetch_cset_version, \
    get_csets_over_threshold, sync_expressions_for_csets, update_cset_metadata_from_objs
from enclave_wrangler.utils import EnclaveWranglerErr

DESC = "Resolve any failures resulting from fetching data from the Enclave's objects API."
err_500_msg = "Tried to fetch members for cset {}, but got an error 500. Suspecting this is due to having more " \
    "members than the Enclave API will allow to fetch. Marking it in the DB as such a suspected case. This cset will " \
    "have to be fetched some other way."


def _report_success(
    cset_ids: Union[int, List[int]], fetch_audit_row_lookup: Dict[int, Dict], comment_addition: str = None, use_local_db=False
):
    """Report success fetch success for given concept sets.
    todo: kind of weird to pass a lookup. Maybe do that beforehand and pass row dict"""
    cset_ids = [cset_ids] if not isinstance(cset_ids, list) else cset_ids
    success_rows = []
    for cset_id in cset_ids:
        row = fetch_audit_row_lookup[cset_id]
        if comment_addition:
            row['comment'] = row['comment'] + '; ' + \
                 ('Success result: ' if not comment_addition.startswith('Success result: ') else '') + comment_addition
        success_rows.append(row)
    fetch_status_set_success(success_rows, use_local_db)


def _ad_hoc_detect_and_delete_discarded_drafts(schema=SCHEMA, local=False):
    """Check all csets currently marked draft in the DB, check if discarded, and handle."""
    with get_db_connection(schema=schema, local=local) as con:
        rows: List[List[int]] = sql_query(
            con, f"SELECT codeset_id FROM code_sets WHERE is_draft = true;", return_with_keys=False)
        draft_ids: List[int] = [x[0] for x in rows]
        cset_versions: List[Dict] = [fetch_cset_version(_id, retain_properties_nesting=True) for _id in draft_ids]
        cset_versions = [x for x in cset_versions if x]  # remove discarded draft empty dicts {}
        csets_and_members: Dict[str, List[Dict]] = {'OMOPConceptSet': cset_versions}
        handle_discarded_drafts(con, csets_and_members, set(draft_ids), report_success=False, use_local_db=local)


def _ad_hoc_sync_draft_expression_items(since='2023-08-15', schema=SCHEMA, local=False):
    """Syncronizes all expression items since specified date.

    Syncs just the presence of them in the DB, not their field values) between the enclave and TermHub
    Default value 2023-08-15: 1 day before we implemented inclusion of drafts. This last ran on 2024/11/16,
    synchronizing all csets that were were created since that date.
    """
    with get_db_connection(schema=schema, local=local) as con:
        rows: List[List[int]] = sql_query(
            con, f"SELECT codeset_id FROM code_sets WHERE created_at > {since};", return_with_keys=False)
        cset_ids: List[int] = [x[0] for x in rows]
        resolve_fetch_failures_0_members(cset_ids, local, schema=schema, force=True)


def handle_discarded_drafts(
    con: Connection, csets_and_members: Dict[str, List[Dict]], queried_cset_ids: Set[int],
    failure_lookup: Dict[int, Dict] = None, report_success=True, use_local_db=False
) -> Set[int]:
    """Determine if drafts have been discarded and, if so, mark resolved and delete from DB.

    todo: if not report_success, no backup of the discarded draft is deleted. Might want to save to disk."""
    if report_success and not failure_lookup:
        raise ValueError("Failure lookup must be provided if reporting success")

    # Detect which cset drafts have been discarded
    fetched_cset_ids: Set[int] = set([x['properties']['codesetId'] for x in csets_and_members['OMOPConceptSet']]) if \
        csets_and_members else set()
    discarded_cset_ids: Set[int] = queried_cset_ids - fetched_cset_ids
    if not discarded_cset_ids:
        return set()
    print(f"Discarded drafts detected; removing from DB and marking resolved: "
          f"{', '.join([str(x) for x in discarded_cset_ids])}")

    # Report success
    # todo: delete the expressions too, and preserve that information.
    # todo: what if all drafts on a container were deleted. delete container too? (no need)
    if report_success:
        codeset_rows = [dict(x) for x in sql_query(
            con, f'SELECT * FROM code_sets WHERE codeset_id {sql_in(discarded_cset_ids)};')]
        codeset_lookup: Dict[int, Dict] = {x['codeset_id']: x for x in codeset_rows}
        for _id in discarded_cset_ids:
            try:
                cset: Dict = codeset_lookup[_id]
            except KeyError:
                continue  # already deleted; this is probably a re-run of a case that was previously handled
            _report_success(
                _id, failure_lookup, f'Discarded draft. Original properties: {json.dumps(cset)}',
                use_local_db)

    # Delete and refresh
    run_sql(con, f'DELETE FROM code_sets WHERE codeset_id {sql_in(discarded_cset_ids)};')
    refresh_derived_tables(con, independent_tables=['code_sets'])

    return discarded_cset_ids


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

    Todo: complex cases: presently only does simple case:
      - isExcluded=true, includeDescendants=false, includeMapped=false
     Ideally we'd also check cases where:
      - isExcluded=true, but if any includeDescendants=true, check concept_ancestor to see if there actually are any
      descendants, and for includeMapped=true, check concept_relationship to see if any mapped.
    """
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
    version_ids: Union[int, List[int]] = None, use_local_db=False, force=False
) -> Tuple[Set[int], Dict[int, Dict]]:
    """Gets list of IDs of failed concetp set versions as well as a lookup for more information about them

    :param force: If any csets are encountered which have already been resolved, will execute the fetch/import process
     instead of skipping
    """
    # Typing modification
    version_ids: List[int] = [version_ids] if version_ids and not isinstance(version_ids, list) else version_ids

    # Lookup failure data in DB
    failures: List[Dict] = select_failed_fetches(use_local_db)
    failure_lookup: Dict[int, Dict] = {int(x['primary_key']): x for x in failures}
    failure_cset_ids: Set[int] = set(version_ids if version_ids else [
        int(x['primary_key']) for x in failures if x['status_initially'] == 'fail-0-members'])

    # Validate & filter
    if not force:
        non_failures_passed: Set[int] = set(version_ids).difference(failure_lookup.keys()) if version_ids else set()
        if bool(version_ids and non_failures_passed):
            print("Warning: Cset IDs were passed to be resolved, but these are no longer failures; skipping them: "
                  f"{', '.join([str(x) for x in non_failures_passed])}", file=sys.stderr)
        failure_cset_ids = failure_cset_ids - non_failures_passed

    return failure_cset_ids, failure_lookup


def resolve_fetch_failures_0_members(
    version_ids: Union[int, List[int]] = None, use_local_db=False, polling_interval_seconds=30, schema=SCHEMA,
    expansion_threshold_seconds=2 * 60 * 60, loop=False, force=False
):
    """Resolve situations where we tried to fetch data from the Enclave, but failed due to the concept set being too new
    resulting in initial fetch of concept set members being 0.
    :param version_ids: Optional concept set version ID to resolve. If not provided, will check database for flagged
    failures.
    :param expansion_threshold_seconds: The length of time that we reasonably expect that the Enclave should take to expand
    :param loop: If True, will run in a loop to keep attempting to fetch. If this is set to False, it's probably
    because the normal DB refresh rate is already high, and this action runs at the end of every refresh (if there are
    any outstanding issus), so it's not really necessary to run these two concurrently.
    todo: version_id: support list of IDs (comma-delimited)
    todo: Performance: Fetch only members, ideally: Even though we are fetching 'members', adding to the cset members
     table requires cset version and container metadata, and the function that does this expects them to be formaatted
     as objects, not as they come from our DB. We can fetch from DB and then convert to objects, but a lot of work for
     small performance gain.
    """
    version_ids = [version_ids] if version_ids and not isinstance(version_ids, list) else version_ids

    print("Resolving fetch failures: ostensibly new (possibly draft) concept sets with >0 expressions but 0 members")
    # Collect failures
    failed_cset_ids_prefilter, failure_lookup = get_failures_0_members(version_ids, use_local_db, force)
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
        failed_cset_ids, failure_lookup_i = get_failures_0_members(version_ids, use_local_db, force)
        failure_lookup.update(failure_lookup_i)

        # Fetch data
        try:
            csets_and_members: Dict[str, List[Dict]] = fetch_cset_and_member_objects(
                codeset_ids=list(failed_cset_ids), flag_issues=False)
        except EnclaveWranglerErr as err:  # Handle new excess item / server error 500 cases
            err2: Dict = err.args[0]
            err3: Dict = err2['error_report']
            # todo: would be good to close initial "status_initially" and open a new one, rather than changing it.
            # todo: would be good to have WHERE clause include table and status_initially cols, too
            if err2['status_code'] == 500 and err3['request'].endswith('links/omopconcepts'):
                err_id = int(err3['request'].split('/')[-3])
                err_cmt = failure_lookup[err_id]['comment'] + 'Received error 500 while trying to resolve fetch ' + \
                    'failures under initial failure status of "fail-0-members". Suspected that this is now a ' + \
                    'case of "fail-exessive-items", so setting status to that.'
                with get_db_connection(schema='', local=use_local_db) as con:
                    run_sql(con, f"UPDATE fetch_audit SET status_initially = 'fail-excessive-items', "
                        f"comment = '{err_cmt}' WHERE primary_key = '{err_id}';")
                failed_cset_ids.remove(err_id)
                if not failed_cset_ids:
                    raise RuntimeError(err_500_msg.format(err_id))
                csets_and_members: Dict[str, List[Dict]] = fetch_cset_and_member_objects(
                    codeset_ids=list(failed_cset_ids), flag_issues=False)

        # Sync updates
        with get_db_connection(schema=schema, local=use_local_db) as con:
            # - identify & report discarded drafts
            # todo: Fix: Somehow it is possible it's actually not a false positive, that csets_and_members can be
            #  unbound. On very rare occassion (so far once every several years), there will be an excess members cset,
            #  which will cause a 500 here. As can be seen above, if it's the only cset, it re-raises the err. Else, it
            #  will re-run csets_and_members. So by the time it gets here, it should not be unbound. But that did
            #  happen: https://github.com/jhu-bids/TermHub/actions/runs/13448793056/job/37579441859
            # noinspection PyUnboundLocalVariable false_positive
            discarded_cset_ids = handle_discarded_drafts(
                con, csets_and_members, failed_cset_ids, failure_lookup, use_local_db=use_local_db)
            # - sync expression item additions or deletions (todo: updates too)
            sync_expressions_for_csets(csets_and_members['OMOPConceptSet'], con, schema)

        if not csets_and_members:
            return  # all failures were discarded

        # - identify persistent, long-lived drafts
        # noinspection PyUnboundLocalVariable false_positive
        cset_is_draft_map.update(
            {x['properties']['codesetId']: x['properties']['isDraft'] for x in csets_and_members['OMOPConceptSet']})
        # - identify / filter success cases & track results
        success_cases: Dict[str, List[Dict]] = deepcopy(csets_and_members)
        success_cases['OMOPConceptSet'] = [x for x in success_cases['OMOPConceptSet'] if x['member_items']]
        success_cset_ids: List[int] = [x['properties']['codesetId'] for x in success_cases['OMOPConceptSet']]
        failed_cset_ids = list(set(failed_cset_ids) - set(success_cset_ids) - set(discarded_cset_ids))
        finalized_draft_ids: List[int] = [x for x in success_cset_ids if not cset_is_draft_map[x]]
        finalized_drafts: List[Dict] = \
            [x['properties'] for x in success_cases['OMOPConceptSet'] if x['properties']['codesetId'] in finalized_draft_ids]

        # Update DB & report success
        if success_cset_ids:
            try:
                with get_db_connection(schema=schema, local=use_local_db) as con:
                    update_cset_metadata_from_objs(finalized_drafts, con)
                    csets_and_members_to_db(con, success_cases, ['OmopConceptSetVersionItem', 'OMOPConcept'], schema)
                print(f"Successfully fetched concept set members for concept set versions: "
                      f"{', '.join([str(x) for x in success_cset_ids])}")
                filtered_ids = [x for x in success_cset_ids if x in failure_lookup]  # todo #1
                _report_success(filtered_ids, failure_lookup, 'Found members', use_local_db)
            except Exception as err:
                reset_temp_refresh_tables(schema)
                raise err

        # Sleep or exit
        if not loop:
            break
        time.sleep(polling_interval_seconds)

    # Reporting
    # - Csets with 0 expansion members
    #  - todo: only detecting simple cases. For more info, see docstring of filter_cset_id_where_0_expanded_members()
    csets_w_no_expanded_members: List[int] = filter_cset_id_where_0_expanded_members(failed_cset_ids)
    if csets_w_no_expanded_members:
        comment = 'There are 0 expansion members because 100% of the expressions are set to isExcluded=true, ' + \
            'includeDescendants=false, and includeMapped=false.'
        print(f'Csets detected matching the following condition; marking them resolved:\n'
              f'- Condition: {comment}\n'
              f'- Cset IDs:', f'{", ".join([str(x) for x in csets_w_no_expanded_members])}')
        filtered_ids = [x for x in csets_w_no_expanded_members if x in failure_lookup]  # todo #1
        _report_success(filtered_ids, failure_lookup, comment, use_local_db)
        failed_cset_ids = list(set(failed_cset_ids) - set(csets_w_no_expanded_members))

    # - Parse drafts from actual failures
    still_draft_cset_ids: Set[int] = set([cset_id for cset_id in failed_cset_ids if cset_is_draft_map[cset_id]])
    if still_draft_cset_ids:
        print(f"Fetch attempted for the following csets, but they still remain drafts and thus still have not had their"
              f" members expanded yet: {', '.join([str(x) for x in still_draft_cset_ids])}")
    non_draft_failure_ids: Set[int] = set(failed_cset_ids) - still_draft_cset_ids

    # - Filter by only if has been finalized longer than we would expect it should take for expansion to be available
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
        filtered_ids = [x for x in list(final_failure_ids) if x in failure_lookup]  # todo #1
        _report_success(filtered_ids, failure_lookup, comment, use_local_db)
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
        "--version-ids",
        type=int,
        nargs='+',
        required=False,
        help="Optional concept set version ID to resolve. If not provided, will check database for flagged failures.")
    parser.add_argument(
        "-i",
        "--polling-interval-seconds",
        required=False,
        default=30,
        help="How often, in seconds, to try to fetch again if fetching still yields 0 members.")
    parser.add_argument(
        "-F",
        "--force",
        action="store_true",
        required=False,
        help="If any csets are encountered which have already been resolved, will execute the fetch/import process "
             "instead of skipping.")
    resolve_fetch_failures_0_members(**vars(parser.parse_args()))


if __name__ == "__main__":
    cli()
