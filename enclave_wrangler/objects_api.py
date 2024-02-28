#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

Resources
  Search: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/search/
  List: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/

TODO's
 1. Consider refactor: Python -> Bash (curl + JQ)
 2. Are the tables in 'datasets' isomorphic w/ 'objects'? e.g. object OmopConceptSetVersionItem == table
 concept_set_version_item_rv_edited_mapped.
 3. All _db funcs / funcs that act on the DB (and unit tests) should be in backend/, not enclave_wrangler.
"""
import json
import os
import sys
from argparse import ArgumentParser

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Union
from urllib.parse import quote, unquote

uquote = lambda s: quote(unquote(s), safe='')   # in case it was already quoted

from sanitize_filename import sanitize

from requests import Response
from sqlalchemy.engine.base import Connection
from typeguard import typechecked

THIS_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_ROOT = THIS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
from enclave_wrangler.config import OBJECT_REGISTRY, OUTDIR_OBJECTS, OUTDIR_CSET_JSON, config
from enclave_wrangler.utils import EnclavePaginationLimitErr, enclave_get, enclave_post, fetch_objects_since_datetime, \
    get_objects_df, get_url_from_api_path, \
    make_objects_request
from enclave_wrangler.models import OBJECT_TYPE_TABLE_MAP, convert_row, get_field_names, field_name_mapping, pkey
from backend.db.utils import SCHEMA, insert_fetch_statuses, insert_from_dict, insert_from_dicts, \
    is_refresh_active, refresh_derived_tables, reset_temp_refresh_tables, refresh_derived_tables, \
    sql_query_single_col, run_sql, get_db_connection
from backend.db.queries import get_concepts
from backend.utils import call_github_action, pdump

DEBUG = False
HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    # "authorization": f"Bearer {config['OTHER_TOKEN']}",
    "Content-type": "application/json",
    #'content-type': 'application/json'
}


BASE_URL = f'https://{config["HOSTNAME"]}'
ONTOLOGY_RID = config['ONTOLOGY_RID']

@typechecked
def get_object_types(verbose=False) -> List[Dict]:
    """Gets object types.
    API docs: https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" "https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objectTypes" | jq

    TODO: @Siggie: Here's what I found that looked interesting:
     ConceptRelationship, ConceptSetBundleItem, ConceptSetTag, ConceptSetVersionChangeAcknowledgement,
     ConceptSuccessorRelationship, ConceptUsageCounts, CsetVersionInfo, CodeSystemConceptSetVersionExpressionItem,
     OMOPConcept, OMOPConceptAncestorRelationship, OMOPConceptChangeConnectors, OMOPConceptSet,
     OMOPConceptSetContainer, OMOPConceptSetReview, OmopConceptChange, OmopConceptDomain, OmopConceptSetVersionItem,
    """
    url = get_url_from_api_path('objectTypes')
    response: Response = enclave_get(url, verbose=verbose)
    return response.json()['data']


def get_link_types(use_cache_if_failure=False) -> List[Union[Dict, str]]:
    """Get link types

    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-linked-objects/

    todo: This doesn't work on Joe's machine, in PyCharm or shell. Works for Siggie. We both tried using
      PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN (we use the same one) instead as well- 2022/12/12
    todo: What is the UUID starting with 00000001?
    todo: Do equivalent of `jq '..|objects|.apiName//empty'` here so that what's returned from response.json() is
      the also a List[str], like what's 'cached' here.

    curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
    "https://unite.nih.gov/ontology-metadata/api/ontology/linkTypesForObjectTypes" --data '{
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
            "00000001-9834-2acf-8327-ecb491e69b5c"
        }
    }' | jq '..|objects|.apiName//empty'
    """
    # cached: 2022/12/12
    cached_types: List[str] = [
        'cohortLinks',
        'cohortVersions',
        'conceptSetBundleItem',
        'conceptSetTag',
        'conceptSetVersionChangeAcknowledgement',
        'conceptSetVersionInfo',
        'conceptSetVersions',
        'conceptSetVersionsCreatedForThisResearchProject',
        'consumedConceptSetVersion',
        'consumingProtocolSection',
        'createdOmopConceptSetVersions',
        'creator',
        'documentationNodeRv',
        'draftCohortLinks',
        'intendedDomainTeam',
        'intendedResearchProject',
        'omopConceptChange',
        'omopConceptDomains',
        'omopConceptSetVersion',
        'omopConceptSetVersionIntendedForDT',
        'omopConceptSetVersionItem',
        'omopConceptSetVersions',
        'omopconceptSet',
        'omopconceptSetChildVersion',
        'omopconceptSetContainer',
        'omopconceptSetParentVersion',
        'omopconceptSetReview',
        'omopconcepts',
        'omopconceptsets',
        'omopvocabularyVersion',
        'producedConceptSetVersion',
        'producingProtocolSection',
        'researchProject',
        'revisedconceptSetVersionChangeAcknowledgement',
        'revisedomopconceptSet',
    ]

    # noinspection PyBroadException
    try:
        data = {
            "objectTypeVersions": {
                "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":  # what RID is this?
                    "00000001-9834-2acf-8327-ecb491e69b5c"  # what UUID is this?
            }
        }
        url = f'{BASE_URL}/ontology-metadata/api/ontology/linkTypesForObjectTypes'
        response = enclave_post(url, data=data)
        # TODO:
        #   change to:
        #   response = enclave_post(url, data=data)
        response_json: List[Dict] = response.json()
        return response_json
    except Exception as err:
        if use_cache_if_failure:
            return cached_types
        raise err


def get_object_links(
    object_type: str, object_id: str, link_type: str, fail_on_error=False, handle_paginated=True,
    return_type: str = ['Response', 'json', 'data'][2], retry_if_empty=False,
    expect_single_item=False,
    verbose = False,

) -> Union[Response, List[Dict]]:
    """Get links of a given type for a given object

    Cavaets
    - If the `link_type` is not valid for a given `object_type`, you'll get a 404 not found.
    """
    return make_objects_request(
        f'{object_type}/{object_id}/links/{link_type}', return_type=return_type, fail_on_error=fail_on_error,
        handle_paginated=handle_paginated, expect_single_item=expect_single_item,
        retry_if_empty=retry_if_empty, verbose=verbose)


# TODO: Why does this not work for Joe, but works for Siggie?:
# {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Default:InvalidArgument', 'errorInstanceId': '96596b59-39cb-4b68-b86f-36089815a22e', 'parameters': {}}
def get_ontologies() -> Union[List, Dict]:
    """Get ontologies
    Docs: https://unite.nih.gov/workspace/documentation/product/api-gateway/list-ontologies"""
    response = enclave_get(f'{BASE_URL}/api/v1/ontologies')
    response_json = response.json()
    return response_json


def link_types() -> List[Dict]:
    """Get link types
    curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
    "https://unite.nih.gov/ontology-metadata/api/ontology/linkTypesForObjectTypes" --data '{
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e": "00000001-9834-2acf-8327-ecb491e69b5c"
        }
    }' | jq '..|objects|.apiName//empty'
    """
    headers = {
        # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        "authorization": f"Bearer {config['OTHER_TOKEN']}",
        'Content-type': 'application/json',
    }
    data = {
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":  # what RID is this?
                "00000001-9834-2acf-8327-ecb491e69b5c"  # what UUID is this?
        }
    }
    api_path = '/ontology-metadata/api/ontology/linkTypesForObjectTypes'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    response = enclave_post(url, data=data)
    response_json = response.json()
    return response_json


# def run(request_types: List[str]) -> Dict[str, Dict]:
#       only being used by cli which is not being used right now
#     """Run"""
#     request_funcs: Dict[str, Callable] = {
#         'objects': get_objects_df,
#         'object_types': get_obj_types,
#         'link_types': get_link_types,
#     }
#     results = {}
#     for req in request_types:
#         results[req] = request_funcs[req]()
#         # if req == 'object_types':
#         #     print('\n'.join([t['apiName'] for t in results[req]['types']]))
#     return results


def download_favorite_objects(fav_obj_names: List[str] = OBJECT_REGISTRY, force_if_exists=False):
    """Download objects of interest"""
    for o in fav_obj_names:
        outdir = os.path.join(OUTDIR_OBJECTS, o)
        exists = os.path.exists(outdir)
        if not exists or (exists and force_if_exists):
            get_objects_df(o, outdir=outdir)


def get_all_bundles():
    """Get all bundles"""
    return make_objects_request('objects/ConceptSetTag', ).json()


def get_bundle_names(prop: str='displayName'):
    """Get bundle names"""
    all_bundles = get_all_bundles()
    return [b['properties'][prop] for b in all_bundles['data']]


def get_bundle(bundle_name):
    """
    call this like: http://127.0.0.1:8000/enclave-api-call/get_bundle/Anticoagulants
    """
    all_bundles = get_all_bundles()
    tag_name = [b['properties']['tagName'] for b in all_bundles['data'] if b['properties']['displayName'] == bundle_name][0]
    return make_objects_request(f'objects/ConceptSetTag/{tag_name}/links/ConceptSetBundleItem', return_type='data', handle_paginated=True)


def get_bundle_codeset_ids(bundle_name):
    """Get bundle codeset IDs"""
    bundle = get_bundle(bundle_name)
    codeset_ids = [b['properties']['bestVersionId'] for b in bundle]
    return list(set(codeset_ids))


# TODO: do together: all_new_objects_to_db() fetch_all_new_objects() all_new_objects_enclave_to_db()
def all_new_objects_to_db(objects: Dict):
    """Update db w/ new objects"""
    # Database updates
    # TODO: (i) What tables to update after this?, (ii) anything else to be done?. Iterate over:
    #  - new_containers: * new containers, * delete & updates to existing containers
    #  - new_csets2:
    #    - the cset properties itself
    #    - expression_items: we might want to delete its previous items as well, because of possible changes
    #      does expression item ID change when you change one of its flags?
    #    - members
    pass


# TODO: do together: all_new_objects_to_db() fetch_all_new_objects() all_new_objects_enclave_to_db()
def fetch_all_new_objects(since: Union[datetime, str]) -> Dict[str, List]:
    """Get new objects needed to update database.

    Resources:
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/#filtering-objects
    https://unite.nih.gov/workspace/data-integration/restricted-view/preview/ri.gps.main.view.af03f7d1-958a-4303-81ac-519cfdc1dfb3
    """
    since = str(since)
    csets_and_members: Dict[str, List] = fetch_cset_and_member_objects(since)
    # TODO:
    researchers = download_all_researchers()
    # TODO:
    projects = get_projects()
    # TODO: what else?
    pass
    return dict(csets_and_members | {'researchers': researchers} | {'projects': projects})


# TODO: do together: all_new_objects_to_db() fetch_all_new_objects() all_new_objects_enclave_to_db()
def all_new_objects_enclave_to_db(since: Union[datetime, str]) -> Dict[str, List]:
    """Get all new objects and update database"""
    objects = fetch_all_new_objects(since)
    all_new_objects_to_db(objects)
    return objects


def csets_and_members_enclave_to_db(
    con: Connection, since: Union[datetime, str] = None, cset_ids: List[int] = None, schema=SCHEMA
) -> bool:
    """Fetch new csets and members, if needed, and then update database with them, returns None is no updates needed"""
    if not (since or cset_ids) or (since and cset_ids):
        raise ValueError('Must pass either: `since` or `cset_ids`, but not both.')
    t0 = datetime.now()
    print('Fetching new data from the N3C data enclave...')

    csets_and_members: Dict[str, List[Dict]] = fetch_cset_and_member_objects(since) if since \
        else fetch_cset_and_member_objects(codeset_ids=cset_ids)
    if not csets_and_members:
        return False

    print(f'  - Fetched new data in {(datetime.now() - t0).seconds} seconds:\n    OBJECT_TYPE: COUNT\n' +
          "\n".join(['    ' + str(k) + ": " + str(len(v)) for k, v in csets_and_members.items()]))
    csets_and_members_to_db(con, csets_and_members, schema)
    return True


def find_termhub_missing_csets(con: Connection = None) -> Set[int]:
    """Find csets that are missing from TermHub"""
    con = con if con else get_db_connection(schema=SCHEMA)
    db_codeset_ids, enclave_codeset_ids = get_bidirectional_csets_sets(con)
    missing_ids_from_db: Set[int] = enclave_codeset_ids.difference(db_codeset_ids)
    return missing_ids_from_db


def fetch_all_csets(filter_results=True) -> List[Dict]:
    """Fetch all concept sets from the enclave

    :param filter_results (bool): If True, will filter out any old draftts from an old, incompatible data model (
    sourceApplicationVersion 1.0), as well as archived csets."""
    csets: List[Dict] = make_objects_request('OMOPConceptSet', return_type='data', handle_paginated=True)
    csets = [cset['properties'] for cset in csets]
    if filter_results:
        archived_containers: List[Dict] = make_objects_request(
            'OMOPConceptSetContainer', query_params={'properties.archived.eq': True}, return_type='data',
            handle_paginated=True)
        archived_container_names = [container['properties']['conceptSetName'] for container in archived_containers]
        csets = [
            cset for cset in csets
            if 'conceptSetNameOMOP' in cset.keys()  # why is it missing sometimes? old data model?
               # - Filter any old drafts from sourceApplicationVersion 1.0. Old data model. No containers, etc. See also:
               #  https://github.com/jhu-bids/TermHub/actions/runs/6489411749/job/17623626419
               and cset['conceptSetNameOMOP']
               and not cset['conceptSetNameOMOP'] in archived_container_names
        ]
    return csets


def get_bidirectional_csets_sets(con: Connection = None) -> Tuple[Set[int], Set[int]]:
    """Find missing csets"""
    # Set 1 of 2: In our database
    con = con if con else get_db_connection(schema=SCHEMA)
    db_codeset_ids: Set[int] = set(sql_query_single_col(con, 'SELECT codeset_id FROM code_sets'))
    # Set 2 of 2: In the enclave
    enclave_codesets = fetch_all_csets()
    # Set difference & return
    enclave_codeset_ids: Set[int] = set([cset['codesetId'] for cset in enclave_codesets])
    return db_codeset_ids, enclave_codeset_ids


def add_missing_csets_to_db(cset_ids: List[int], con: Connection = None, schema=SCHEMA):
    """Add missing concept sets to the DB"""
    try:
        con = con if con else get_db_connection(schema=schema)
        csets_and_members_enclave_to_db(con, cset_ids=cset_ids, schema=schema)
    except Exception:
        reset_temp_refresh_tables(schema)


def find_and_add_missing_csets_to_db(con: Connection = None, schema=SCHEMA):
    """Find and add missing concept sets to the DB"""
    if is_refresh_active():
        print('find_and_add_missing_csets_to_db(): Refresh in progress. Try again when it is not.')
        return
    con = con if con else get_db_connection(schema=schema)
    cset_ids: List[int] = list(find_termhub_missing_csets(con))
    if cset_ids:
        add_missing_csets_to_db(cset_ids, con, schema)
    else:
        print('No missing csets found.')


def fetch_cset_and_member_objects(
    since: Union[datetime, str] = '', codeset_ids: List[int] = [], handle_issues=True, verbose=False
) -> Union[Dict[str, List[Dict]], None]:
    """Get new objects: cset container, cset version, expression items, and member items.

    :param since: datetime or str, e.g. '2023-07-09T01:08:23.547680-04:00'. If present, codeset_ids should be empty.
    :param codeset_ids: List of IDs. If present, since should be empty. Will fetch containers, versions, items, and
    members related to these code set IDs.
    :param handle_issues: If True, will flag issues for cset members/items unable to fetch to the fetch audit/status table

    todo: enclave API returns jagged rows (different lengths). E.g. for OMOPConceptSet, if it fetches a cset that does
     not have a value set for the field 'updateMessage', that field will not appear in the object/dictionary.
    todo: refactor so that, (a) ideally for both flat and hierarchical, containers get returned with a 'csets' key, and
     a 'properties' (b) key. Maybe I should just change this so that only hierarchical has these nested objects?, (c)
     add a third option to return both (totally) flat and hierarchical, since both might be helpful?
     The main thing prompting this is that csets_and_members_to_db() needs an 'archived' property from container, so
     I needed to refactor that function to do a lookup to get the container, which is messy. Whenever I make this
     change, it will be a breaking change at the very least for csets_and_members_to_db() both in terms of no longer
     needing to do this lookup, and also dealing properly w/ how the data is returned from this func.
    TODO: @joeflack4, if new container but it has no versions, should still fetch it. right now not doing that
            and, when metadata updated on container or version, need to fetch (but not bother with members and items)

    Resources:
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/#filtering-objects
    https://unite.nih.gov/workspace/data-integration/restricted-view/preview/ri.gps.main.view.af03f7d1-958a-4303-81ac-519cfdc1dfb3

    About: call_github_action() usage
    - This happens at the end of the script. It will run an action to resolve any issues where we failed to fetch data
    from the enclave.

    :return
      - cset containers
      - cset versions
          - member items
          - expression items
      - member items
      - expression items
    """

    # codeset_ids_to_ignore = [938394329] # Hope Termhub Test (v2), 53K concepts. taking forever
    # Concept set versions
    if not (since or codeset_ids) or (since and codeset_ids):
        raise RuntimeError('Must pass either: `since` or `codeset_ids`, but not both.')
    print(' - fetching cset versions')
    if codeset_ids and not since:
        cset_versions: List[Dict] = [fetch_cset_version(_id, retain_properties_nesting=True) for _id in codeset_ids]
    else:
        cset_versions: List[Dict] = fetch_objects_since_datetime('OMOPConceptSet', since, verbose) or []
    # - Filter any old drafts from sourceApplicationVersion 1.0. Old data model. No containers, etc. See also:
    #  https://github.com/jhu-bids/TermHub/actions/runs/6489411749/job/17623626419
    cset_versions = [x for x in cset_versions if x['properties']['conceptSetNameOMOP']]
    cset_versions_by_id: Dict[int, Dict] = {cset['properties']['codesetId']: cset for cset in cset_versions}
    del cset_versions
    print(f'   - retrieved {len(cset_versions_by_id)} versions')

    # Containers
    print(f' - fetching containers for {len(cset_versions_by_id)} versions')
    containers_ids = [x['properties']['conceptSetNameOMOP'] for x in cset_versions_by_id.values()]
    cset_containers: List[Dict] = []
    for _id in containers_ids:
        # todo: will a container ever be paginated? can drop this param, though shouldn't matter
        container: List[Dict] = make_objects_request(
            'OMOPConceptSetContainer', query_params={'properties.conceptSetId.eq': _id}, verbose=verbose,
            return_type='data', handle_paginated=True)
        if not container:
            raise ValueError(f'Enclave API returned cset version with container of id {_id}, but failed to call data '
                             f'for that specific container.')
        cset_containers.append(container[0]['properties'])

    # Returning None if no data
    if not cset_containers and not cset_versions_by_id:
        return

    # Expression items & concept set members
    expression_items = []
    member_items = []
    print(f' - fetching expressions/members for {len(cset_versions_by_id)} versions:')
    i = 0
    for version_id, cset in cset_versions_by_id.items():
        i += 1
        print(f'   - {i}: {version_id}')
        # todo: if failed to get expression items, should we not check for members? maybe ok because flagged
        try:
            cset['expression_items']: List[Dict] = \
                get_concept_set_version_expression_items(version_id, return_detail='full')
        except EnclavePaginationLimitErr as err:
            cset['expression_items']: List[Dict] = err.args[1]['results_prior_to_error']
            if handle_issues:
                insert_fetch_statuses([{'table': 'code_sets', 'primary_key': version_id, 'status_initially':
                    'fail-excessive-items', 'comment':
                    f"Failed after {len(cset['expression_items'])} expression_items."}])
                call_github_action('resolve-fetch-failures-excess-items')
        try:
            cset['member_items']: List[Dict] = get_concept_set_version_members(version_id, return_detail='full')
        except EnclavePaginationLimitErr as err:
            cset['member_items']: List[Dict] = err.args[1]['results_prior_to_error']
            if handle_issues:
                insert_fetch_statuses([{'table': 'code_sets', 'primary_key': version_id, 'status_initially':
                    'fail-excessive-members', 'comment': f"Failed after {len(cset['member_items'])} members."}])
                call_github_action('resolve-fetch-failures-excess-items')
        if not cset['member_items'] and cset['expression_items'] and not cset['properties']['isDraft'] and handle_issues:
            insert_fetch_statuses([{
                'table': 'code_sets', 'primary_key': version_id, 'status_initially': 'fail-0-members',
                'comment': f"Fetched 0 members after fetching {len(cset['expression_items'])} items."}])
            call_github_action('resolve_fetch_failures_0_members.yml', {'version_id': str(version_id)})

        expression_items.extend(cset['expression_items'])
        member_items.extend(cset['member_items'])

    return {'OMOPConceptSetContainer': cset_containers, 'OMOPConceptSet': list(cset_versions_by_id.values()),
            'OmopConceptSetVersionItem': expression_items, 'OMOPConcept': member_items}


def concept_set_members__from_csets_and_members_to_db(con: Connection, csets_and_members: Dict[str, List[Dict]]):
    """Take a 'csets_and_members' object and take what is needed to insert data into concept_set_members table."""
    container_lookup = {x['conceptSetId']: x for x in csets_and_members['OMOPConceptSetContainer']}
    for cset in csets_and_members['OMOPConceptSet']:
        container = container_lookup[cset['properties']['conceptSetNameOMOP']]
        concept_set_members__cset_rows_to_db(con, cset, cset['member_items'], container)

def csets_and_members_to_db(con: Connection, csets_and_members: Dict[str, List[Dict]], schema=SCHEMA):
    """Update database with csets and members.
    todo: add_object_to_db(): support multiple objects with single insert"""
    # Core cset tables: with normal, single primary keys
    for object_type_name, objects in csets_and_members.items():
        print(f'Running SQL inserts in core tables for: {object_type_name}...')
        t0 = datetime.now()
        objects = [obj['properties'] if 'properties' in obj else obj for obj in objects]
        add_objects_to_db(con, object_type_name, objects)
        t1 = datetime.now()
        print(f'  - completed in {(t1 - t0).seconds} seconds')

    # Core cset tables with: composite primary keys
    print('Running SQL inserts in core tables for: concept_set_members...')
    t2 = datetime.now()
    concept_set_members__from_csets_and_members_to_db(con, csets_and_members)
    print(f'  - concept_set_members completed in {(datetime.now() - t2).seconds} seconds')

    # Derived tables
    refresh_derived_tables(con, schema)


def fetch_object_by_id(
    object_type_name: str, object_id: Union[int, str], id_field: str = None, retain_properties_nesting=False,
    verbose=False,
) -> Dict:
    """Fetch object by its id
    :param retain_properties_nesting: If False, returns x['properties'] instead of x for any x returned from
    make_objects_request(). When this is done, x['rid'] is also lost, but we have yet to find a use case for that."""
    err = f'fetch_object_by_id(): Did not pass optional param `id_field`, but also could not automatically resolve ' \
          f'the primary key / ID field for {object_type_name}. Try passing the `id_field` manually, or adding it to' \
          f' `PKEYS` in `objects_api.py`.'
    id_field = id_field if id_field else pkey(object_type_name)
    if not id_field:
        raise RuntimeError(err)
    # query_params = [get_query_param(id_field, 'eq', str(object_id))]
    matches: List[Dict] = make_objects_request(
        object_type_name,
        query_params={f'properties.{id_field}.eq': str(object_id)},
        return_type='data', verbose=verbose, handle_paginated=True)
    if not matches:
        return {}
    obj: Dict = matches[0] if retain_properties_nesting else matches[0]['properties']
    return obj


def fetch_cset_version(object_id: int, retain_properties_nesting=False) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OMOPConceptSet', object_id, 'codesetId', retain_properties_nesting)


def fetch_cset_container(object_id: str, fail_on_error=False, retain_properties_nesting=False, verbose=False) -> Dict:
    """Get object from enclave"""
    return make_objects_request(
        f'OMOPConceptSetContainer/{object_id}', fail_on_error=fail_on_error,
        verbose=verbose, return_type='data', expect_single_item=True)


def fetch_cset_member_item(object_id: int, retain_properties_nesting=False) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OMOPConcept', object_id, 'conceptId', retain_properties_nesting)


def fetch_concept(object_id: int, retain_properties_nesting=False) -> Dict:
    """Get object from enclave"""
    return fetch_cset_member_item(object_id, retain_properties_nesting)


def fetch_cset_expression_item(object_id: int, retain_properties_nesting=False) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OmopConceptSetVersionItem', object_id, 'itemId', retain_properties_nesting)


def add_objects_to_db(
    con: Connection, object_type_name: str, objects: List[Dict], tables: List[str] = None, skip_if_already_exists=True
):
    """Add object to db"""
    tables = tables if tables else OBJECT_TYPE_TABLE_MAP[object_type_name]
    for table in tables:
        table_objects: List[Dict] = [convert_row(object_type_name, table, obj) for obj in objects]
        insert_from_dicts(con, table, table_objects, skip_if_already_exists)


def add_object_to_db(
    con: Connection, object_type_name: str, obj: Dict, tables: List[str] = None, skip_if_already_exists=True
):
    """Add object to db"""
    tables = tables if tables else OBJECT_TYPE_TABLE_MAP[object_type_name]
    for table in tables:
        table_obj: Dict = convert_row(object_type_name, table, obj)
        insert_from_dict(con, table, table_obj, skip_if_already_exists)


# todo: maybe: refactor to use object_type_name and not table, then use dict to figure which tables to update and how
def fetch_object_and_add_to_db(
    con: Connection, object_type_name: str, object_id: Union[int, str], tables: List[str] = None,
    skip_if_already_exists=True
) -> Dict:
    """Fetch object and add to db"""
    obj: Dict = fetch_object_by_id(object_type_name, object_id)
    add_object_to_db(con, object_type_name, obj, tables, skip_if_already_exists)
    return obj


def concept_set_container_enclave_to_db(
    con: Connection, object_id: str, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Given ID, get object's current state from the enclave, and add it the DB"""
    return fetch_object_and_add_to_db(con, 'OMOPConceptSetContainer', object_id, tables, skip_if_already_exists)


def code_sets_enclave_to_db(
    con: Connection, object_id: int, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Given ID, get object's current state from the enclave, and add it the DB"""
    return fetch_object_and_add_to_db(con, 'OMOPConceptSet', object_id, tables, skip_if_already_exists)


def cset_version_enclave_to_db(
    con: Connection, object_id: int, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Alias for: code_sets_enclave_to_db()"""
    return code_sets_enclave_to_db(con, object_id, tables, skip_if_already_exists)


# todo: Would this be better just to get the container and sync any non-uploaded versions to the DB?
# TODO: @Siggie will continue this to populate additional derived tables that need to be populated
#       is it actually adding the version items?
def cset_container_and_version_enclave_to_db(con: Connection, container_name: str, version_id: int, skip_if_already_exists=True):
    """pass"""
    concept_set_container_enclave_to_db(con, container_name, None, skip_if_already_exists)
    code_sets_enclave_to_db(con, version_id, None, skip_if_already_exists)


def concept_set_version_item_enclave_to_db(
    con: Connection, object_id: str, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Given ID, get object's current state from the enclave, and add it the DB"""
    return fetch_object_and_add_to_db(con, 'OmopConceptSetVersionItem', object_id, tables, skip_if_already_exists)


def concept_expression_enclave_to_db(
    con: Connection, object_id: str, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Alias for: concept_set_version_item_enclave_to_db()"""
    return concept_set_version_item_enclave_to_db(con, object_id, tables, skip_if_already_exists)


def concept_enclave_to_db(
    con: Connection, object_id: int, tables: List[str] = None, skip_if_already_exists=True
) -> Dict:
    """Given ID, get object's current state from the enclave, and add it the DB"""
    return fetch_object_and_add_to_db(con, 'OMOPConcept', object_id, tables, skip_if_already_exists)


# todo: New func for multiple csets in a single insert?
# TODO: @Sigfried: I have some 'not sure' fields, I'm not sure if the field in concept_set_members should be taken from
#  the cset or the member. I think the cset, but not 100% sure. And in one case, got from container. - joeflack4
def concept_set_members__cset_rows_to_db(con: Connection, cset: Dict, members: List[Dict], container: Dict):
    """Insert multiple rows into concept_set_members"""
    cset: Dict = cset['properties'] if 'properties' in cset else cset
    members: List[Dict] = [x['properties'] if 'properties' in x else x for x in members]
    table_objs: List[Dict] = [{
        'codeset_id': cset['codesetId'],
        'concept_id': member['conceptId'],
        'concept_set_name': cset['conceptSetNameOMOP'],
        'is_most_recent_version': cset['isMostRecentVersion'], # not sure: is this correct?
        'version': cset['version'], # not sure: is this correct?
        'concept_name': member['conceptName'],
        'archived': container['archived'], # not sure: is this correct?
    } for member in members]
    insert_from_dicts(con, 'concept_set_members', table_objs, skip_if_already_exists=True)


# deprecated?: The only function that calls this, concept_set_members_enclave_to_db(), has been deprecated
def concept_set_members__row_to_db(con: Connection, cset_enclave_obj: Dict, concept_enclave_obj: Dict, container: Dict):
    """Insert row into concept_set_members
    todo: Refactor this function (which may not even be needed / used now) to create table_obj the same way as done in
     concept_set_members__cset_rows_to_db(). Maybe share code between the two funcs.
    todo: 'not sure' fields: see comments for concept_set_members__cset_rows_to_db()"""
    cset_enclave_obj = \
        cset_enclave_obj['properties'] if 'properties' in cset_enclave_obj else cset_enclave_obj
    concept_enclave_obj = \
        concept_enclave_obj['properties'] if 'properties' in concept_enclave_obj else concept_enclave_obj
    table_obj = {
        'codeset_id': cset_enclave_obj['codesetId'],
        'concept_id': concept_enclave_obj['conceptId'],
        'concept_set_name': cset_enclave_obj['conceptSetNameOMOP'],
        'is_most_recent_version': cset_enclave_obj['isMostRecentVersion'], # not sure: is this correct?
        'version': cset_enclave_obj['version'], # not sure: is this correct?
        'concept_name': concept_enclave_obj['conceptName'],
        'archived': container['archived'], # not sure: is this correct?
    }
    insert_from_dict(con, 'concept_set_members', table_obj)


# deprecated: do we really need it? Not used anywhere currently due to refactors
def concept_set_members_enclave_to_db(con: Connection, codeset_id: int, concept_id: int, members_table_only=False):
    """Given ID, get object's current state from the enclave, and add it the DB
    # todo: allow to insert handle multiple objects at once"""
    code_set_enclave_obj: Dict = fetch_object_by_id('OMOPConceptSet', codeset_id)
    concept_enclave_obj: Dict = fetch_object_by_id('OMOPConcept', concept_id)
    if not members_table_only:
        add_object_to_db(
            con, 'OMOPConceptSet', code_set_enclave_obj, OBJECT_TYPE_TABLE_MAP['OMOPConceptSet'])
        add_object_to_db(con, 'OMOPConcept', concept_enclave_obj, OBJECT_TYPE_TABLE_MAP['OMOPConcept'])
    concept_set_members__row_to_db(con, code_set_enclave_obj, concept_enclave_obj)

def items_to_atlas_json_format(items):
    """Convert version items to atlas json format"""
    flags = ['includeDescendants', 'includeMapped', 'isExcluded']

    items = [item['properties'] if 'properties' in item else item for item in items]

    try:
        concept_ids = [i['conceptId'] for i in items]
    except Exception as err:
        concept_ids = [i['concept_id'] for i in items]

    # getting individual concepts from objects api is way too slow
    concepts = get_concepts(concept_ids, table='concept')
    concepts = {c['concept_id']: c for c in concepts}
    items_jsn = []
    mapped_atlasjson_fields = get_field_names('atlasjson')
    for item in items:
        j = {}
        for flag in flags:
            j[flag] = item[flag]
        c = concepts[item['conceptId']]
        jc = {}
        for field in mapped_atlasjson_fields:
            jc[field] = c[field_name_mapping('atlasjson', 'concept', field)]
        # was:
        # jc['CONCEPT_ID'] = c['concept_id']
        # jc['CONCEPT_CLASS_ID'] = c['concept_class_id']
        # jc['CONCEPT_CODE'] = c['concept_code']
        # jc['CONCEPT_NAME'] = c['concept_name']
        # jc['DOMAIN_ID'] = c['domain_id']
        # jc['INVALID_REASON'] = c['invalid_reason']
        # jc['STANDARD_CONCEPT'] = c['standard_concept']
        # jc['VOCABULARY_ID'] = c['vocabulary_id']
        # jc['VALID_START_DATE'] = c['valid_start_date']
        # jc['VALID_END_DATE'] = c['valid_end_date']
        j['concept'] = jc
        items_jsn.append(j)
    return items_jsn


# todo: split into get/update
def get_codeset_json(codeset_id, con: Connection = None, use_cache=True, set_cache=True) -> Dict:
    """Get code_set jSON"""
    conn = con if con else get_db_connection()
    if use_cache:
        jsn = sql_query_single_col(conn, f"""
            SELECT json
            FROM concept_set_json
            WHERE codeset_id = {int(codeset_id)}
        """)
        if jsn:
            return jsn[0]
    cset = make_objects_request(f'objects/OMOPConceptSet/{codeset_id}', return_type='data', expect_single_item=True)
    container = make_objects_request(
        f'objects/OMOPConceptSetContainer/{uquote(cset["conceptSetNameOMOP"], safe="")}',
        return_type='data', expect_single_item=True)
    items = get_concept_set_version_expression_items(codeset_id, handle_paginated=True, return_detail='full')
    items_jsn = items_to_atlas_json_format(items)

    junk = """ What an item should look like for ATLAS JSON import format:
    {
      "concept": {
        "CONCEPT_CLASS_ID": "Prescription Drug",
        "CONCEPT_CODE": "b76de34a-d473-4405-b12b-56ad7a577024",
        "CONCEPT_ID": 835572,
        "CONCEPT_NAME": "nirmatrelvir and ritonavir KIT [paxlovid]",
        "DOMAIN_ID": "Drug",
        "INVALID_REASON": "V",
        "INVALID_REASON_CAPTION": "Valid",
        "STANDARD_CONCEPT": "C",
        "STANDARD_CONCEPT_CAPTION": "Classification",
        "VOCABULARY_ID": "SPL",
        "VALID_START_DATE": "2021-12-21",
        "VALID_END_DATE": "2099-12-30"
      },
      "isExcluded": false,
      "includeDescendants": true,
      "includeMapped": true
    },
    what comes back from OMOPConcept call (objects/OMOPConcept/43791703):
    {
      "properties": {
        "conceptId": 43791703,
        "conceptName": "0.3 ML Dalteparin 227 MG/ML Injectable Solution [Fragmin] Box of 20",
        "domainId": "Drug",
        "standardConcept": "S",
        "validEndDate": "2099-12-31",
        "conceptClassId": "Quant Branded Box",
        "vocabularyId": "RxNorm Extension",
        "conceptCode": "OMOP715886",
        "validStartDate": "2017-08-24"
      },
      "rid": "ri.phonograph2-objects.main.object.53325393-1ee9-4b25-9a1d-a7ed8db3a3b4"
    }
    items from above:
    {
        "itemId": "224241803-43777620",
        "includeDescendants": false,
        "conceptId": 43777620,
        "isExcluded": false,
        "codesetId": 224241803,
        "includeMapped": false
      },
    """

    jsn = {
        'concept_set_container': container,
        'version': cset,
        'items': items_jsn,
    }
    sql_jsn = json.dumps(jsn)
    # sql_jsn = str(sql_jsn).replace('\'', '"')

    if set_cache:
        try:
            run_sql(conn, f"""
                INSERT INTO concept_set_json VALUES (
                    {codeset_id},
                    (:jsn)::json
                )
            """, {'jsn': sql_jsn})
        except Exception as err:
            print('trying to insert\n')
            print(sql_jsn)
            raise err
        finally:
            if not con:
                conn.close()
    return jsn


# todo: split into get/update
def get_n3c_recommended_csets(save=False):
    """Get N3C recommended concept sets"""
    codeset_ids = get_bundle_codeset_ids('N3C Recommended')
    if not save:
        return codeset_ids
    if not os.path.exists(OUTDIR_CSET_JSON):
        os.mkdir(OUTDIR_CSET_JSON)
    for codeset_id in codeset_ids:
        jsn = get_codeset_json(codeset_id)
        fname = f"{jsn['version']['conceptSetVersionTitle']}.{jsn['version']['codesetId']}.json"
        fname = sanitize(fname)
        print(f'saving {fname}')
        outpath = os.path.join(OUTDIR_CSET_JSON, fname)
        with open(outpath, 'w') as f:
            json.dump(jsn, f)


def enclave_api_call_caller(name:str, params) -> Dict:
    """Calls the appropriate enclave API function based on name and params"""
    lookup = {
        'get_all_bundles': get_all_bundles,
        'get_bundle_names': get_bundle_names,
        'get_bundle': get_bundle,
        'get_bundle_codeset_ids': get_bundle_codeset_ids,
        'get_n3c_recommended_csets': get_n3c_recommended_csets,
        'get_codeset_json': get_codeset_json,
    }
    func = lookup[name]
    return func(*params)


# TODO: Download /refresh: tables using object ontology api (e.g. full concept set info from enclave) #189 -------------
# TODO: func 1/3: Do this before refresh_tables_for_object() and refresh_favorite_objects()
#   - get_objects_df() updates above

#  Issue: https://github.com/jhu-bids/TermHub/issues/189 PR: https://github.com/jhu-bids/TermHub/pull/221
# TODO: func 3/3: config.py needs updating for favorite datsets / objects
def refresh_favorite_objects():
    """Refresh objects of interest

    todo's
      - create github action that runs this hourly using CLI
      - add this as a CLI param
    """
    pass


# TODO: func 2/3: Before starting, define a graph / dict (in config.py?) of object types and their tables
def refresh_tables_for_object():
    """Get all latest objects and refresh tables related to object"""
    # Get new objects
    # new_objects = get_new_objects()
    # Refresh tables
    pass


# </Download /refresh: tables using object ontology api (e.g. full concept set info from enclave) #189 -----------------


def get_concept_set_version_expression_items(
    codeset_id: Union[str, int], return_detail, handle_paginated=True, fail_on_error=True
) -> List[Dict]:
    """Get concept set version expression items"""
    codeset_id = str(codeset_id)
    items: List[Dict] = get_object_links(
        object_type='OMOPConceptSet',
        object_id=codeset_id,
        link_type='OmopConceptSetVersionItem',
        handle_paginated=handle_paginated,
        fail_on_error=fail_on_error)
    if return_detail == 'id':
        return [x['properties']['itemId'] for x in items]
    return items


def get_concept_set_version_members(
    codeset_id: Union[str, int], return_detail, handle_paginated=True, verbose=False, fail_on_error=True
) -> List[Dict]:
    """Get concept set members"""
    codeset_id = str(codeset_id)
    members: List[Dict] = get_object_links(
        object_type='OMOPConceptSet',
        object_id=codeset_id,
        link_type='omopconcepts',
        handle_paginated=handle_paginated,
        verbose=verbose,
        fail_on_error=fail_on_error)
    if return_detail == 'id':
        return [x['properties']['conceptId'] for x in members]
    return members


def download_all_researchers(verbose=False) -> List[Dict]:
    """Get researcher objects
    Researcher exploration page:
    https://unite.nih.gov/workspace/hubble/exploration?objectTypeRid=ri.ontology.main.object-type.70d7defa-4914-422f-83da-f45c28befd5a
    """
    object_name = 'Researcher'
    data: List[Dict] = make_objects_request(object_name, handle_paginated=True, return_type='data', verbose=verbose)
    return data


def get_researcher(multipass_id: str, verbose=False) -> Dict:
    """Get researcher objects
    Researcher exploration page:
    https://unite.nih.gov/workspace/hubble/exploration?objectTypeRid=ri.ontology.main.object-type.70d7defa-4914-422f-83da-f45c28befd5a
    """
    object_name = 'Researcher'
    data: List[Dict] = make_objects_request(object_name + '/' + multipass_id, expect_single_item=True, return_type='data', verbose=verbose)
    return data


def get_projects(verbose=False) -> List[Dict]:
    """Get project objects
    Projects exploration page:
    https://unite.nih.gov/workspace/hubble/exploration?objectTypeRid=ri.ontology.main.object-type.84d08d30-bbea-4e3d-a995-040057391a71
    """
    object_name = 'ResearchProject'
    data: List[Dict] = make_objects_request(object_name, handle_paginated=True, return_type='data', verbose=verbose)
    return data


def cli():
    """Command line interface for package."""
    parser = ArgumentParser(
        prog='Enclave wrangler objects API',
        description='Tool for working w/ the Palantir Foundry enclave API.')

    # Old args
    # parser.add_argument(
    #     '-a', '--auth_token_env_var',
    #     default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
    #     help='Name of the environment variable holding the auth token you want to use')
    # todo: 'objects' alone doesn't make sense because requires param `object_type`
    # parser.add_argument(
    #     '-r', '--request-types',
    #     nargs='+', default=['object_types', 'objects', 'link_types'],
    #     help='Types of requests to make to the API.')
    # parser.add_argument(
    #     '-f', '--downoad-favorite-objects',
    #     action='store_true', help='Download favorite objects as CSV and JSON.')
    # kwargs = parser.parse_args()
    # kwargs_dict: Dict = vars(kwargs)
    # if kwargs_dict['download_favorite_objects']:
    #     download_favorite_objects()
    # else:
    #     del kwargs_dict['download_favorite_objects']
    #     run(**kwargs_dict)

    # New args added from 9/12/2023
    parser.add_argument(
        '-A', '--find-and-add-missing-csets-to-db', action='store_true',
        help='Find and add missing csets to the DB.')
    parser.add_argument(
        '-f', '--find-missing-csets', action='store_true',
        help='Find missing csets, either in enclave and not in TermHub, or vice versa.')
    parser.add_argument(
        '-d', '--refresh-derived', action='store_true',
        help='Just refresh the derived tables.')
    args: Dict = vars(parser.parse_args())
    commands_to_run = [k for k, v in args.items() if v]
    if 'find_missing_csets' in commands_to_run:
        get_bidirectional_csets_sets()
    if 'find_and_add_missing_csets_to_db' in commands_to_run:
        find_and_add_missing_csets_to_db()
    if'refresh_derived' in commands_to_run:
        with get_db_connection() as con:
            refresh_derived_tables(con)


if __name__ == '__main__':
    cli()
