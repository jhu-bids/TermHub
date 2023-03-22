#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

Resources
  Search: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/search/
  List: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/

TODO's
 1. Consider refactor: Python -> Bash (curl + JQ)
 2. Are the tables in 'datasets' isomorphic w/ 'objects'? e.g. object OMOPConceptSetVersionItem == table
 concept_set_version_item_rv_edited_mapped.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Union
from urllib.parse import quote
from sanitize_filename import sanitize

from requests import Response
from sqlalchemy.engine.base import Connection
from typeguard import typechecked

# import requests
# import pyarrow as pa
# import asyncio

from enclave_wrangler.config import FAVORITE_OBJECTS, OUTDIR_OBJECTS, OUTDIR_CSET_JSON, config, TERMHUB_CSETS_DIR
from enclave_wrangler.utils import enclave_get, enclave_post, get_objects_df, get_query_param, get_url_from_api_path, \
    make_objects_request, \
    handle_paginated_request, handle_response_error
from enclave_wrangler.models import convert_row, get_field_names, field_name_mapping
# from enclave_wrangler.utils import log_debug_info
from backend.db.utils import insert_from_dict, sql_query_single_col, run_sql, get_db_connection
from backend.db.queries import get_concepts
# from backend.utils import pdump


HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    # "authorization": f"Bearer {config['OTHER_TOKEN']}",
    "Content-type": "application/json",
    #'content-type': 'application/json'
}
DEBUG = False


# got rid of EnclaveClient class. Replacing its init properties with globals:
# was:
#   self.headers = HEADERS                            # not used
#   self.debug = DEBUG                                # not used
#   self.base_url = f'https://{config["HOSTNAME"]}'
#   self.ontology_rid = config['ONTOLOGY_RID']
#   self.outdir_root = TERMHUB_CSETS_DIR              # not used

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


def get_object_links(object_type: str, object_id: str, link_type: str) -> Response:
    """Get links of a given type for a given object

    Cavaets
    - If the `link_type` is not valid for a given `object_type`, you'll get a 404 not found.
    """
    return make_objects_request(f'objects/{object_type}/{object_id}/links/{link_type}')


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


def download_favorite_objects(fav_obj_names: List[str] = FAVORITE_OBJECTS, force_if_exists=False):
    """Download objects of interest"""
    for o in fav_obj_names:
        outdir = os.path.join(OUTDIR_OBJECTS, o)
        exists = os.path.exists(outdir)
        if not exists or (exists and force_if_exists):
            get_objects_df(o, outdir=outdir)


def get_all_bundles():
    """Get all bundles"""
    return make_objects_request('objects/ConceptSetTag').json()


def get_bundle_names(prop: str='displayName'):
    """Get bundle names"""
    all_bundles = get_all_bundles()
    return [b['properties'][prop] for b in all_bundles['data']]


def get_bundle(bundle_name):
    """
    call this like: http://127.0.0.1:8000/enclave-api-call/get_bundle/Anticoagulants
    """
    all_bundles = get_all_bundles()
    tagName = [b['properties']['tagName'] for b in all_bundles['data'] if b['properties']['displayName'] == bundle_name][0]
    return make_objects_request(f'objects/ConceptSetTag/{tagName}/links/ConceptSetBundleItem').json()['data']


def get_bundle_codeset_ids(bundle_name):
    """Get bundle codeset IDs"""
    bundle = get_bundle(bundle_name)
    codeset_ids = [b['properties']['bestVersionId'] for b in bundle]
    return codeset_ids


# TODO:
def update_db_with_new_objects(objects=None):
    """Update db w/ new objects"""
    objects: Dict[str, List] = objects if objects else get_new_cset_and_member_objects()
    # 2. Database updates
    # TODO: (i) What tables to update after this?, (ii) anything else to be done?. Iterate over:
    #  - new_containers: * new containers, * delete & updates to existing containers
    #  - new_csets2:
    #    - the cset properties itself
    #    - expression_items: we might want to delete its previous items as well, because of possible changes
    #      does expression item ID change when you change one of its flags?
    #    - members
    pass


# TODO: finish this
def get_all_new_objects(since: Union[datetime, str]) -> Dict[str, List]:
    """Get new objects needed to update database.

    Resources:
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/#filtering-objects
    https://unite.nih.gov/workspace/data-integration/restricted-view/preview/ri.gps.main.view.af03f7d1-958a-4303-81ac-519cfdc1dfb3
    """
    since = str(since)
    csets_and_members: Dict[str, List] = get_new_cset_and_member_objects(since, return_type='flat')
    # TODO:
    researchers = get_researchers()
    # TODO:
    projects = get_projects()
    # TODO: what else?
    pass
    return dict(csets_and_members | {'researchers': researchers} | {'projects': projects})


# TODO
#  - future: updates: if someone made a change to something we already fetched, how do we know?
#  - how to refresh when user creates something?: (a) have the user refresh the db immediately after creating something,
#    and just download everything since list 'since' date? Or (b) fetch only what they updated (if so, we can't do
#    inserts; we have to do updates on IDs)
def get_new_cset_and_member_objects(since: Union[datetime, str], return_type=['flat', 'hierarchical'][0]) -> Dict[str, List]:
    """Get new objects: cset container, cset version, expression items, and member items.

    Resources:
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/#filtering-objects
    https://unite.nih.gov/workspace/data-integration/restricted-view/preview/ri.gps.main.view.af03f7d1-958a-4303-81ac-519cfdc1dfb3

    :return (return_type == 'flat' (default)):
      - cset containers
      - cset versions
      - member items
      - expression items
    :return (return_type == 'hierarchical'):
      - cset containers
      - cset versions
        - member items
        - expression items
    """
    since = str(since)

    # Concept set versions
    cset_versions: List[Dict] = make_objects_request(
        'OMOPConceptSet', query_params=[get_query_param('createdAt', 'gt', since)])

    # Containers
    containers_ids = [x['properties']['conceptSetNameOMOP'] for x in cset_versions]
    container_params = [get_query_param('conceptSetId', 'eq', x) for x in containers_ids]
    cset_containers: List[Dict] = make_objects_request(
        'OMOPConceptSetContainer', query_params=container_params, verbose=True)

    # Expression items & concept set members
    cset_versions_with_concepts: List[Dict] = []
    flat_expression_items = []
    flat_member_items = []
    for cset in cset_versions:
        version: int = cset['properties']['codesetId']
        # Hierarchical
        cset['expression_items']: List[Dict] = get_concept_set_version_expression_items(version, return_detail='full')
        cset['member_items']: List[Dict] = get_concept_set_version_members(version, return_detail='full')
        cset_versions_with_concepts.append(cset)
        # Flat
        flat_expression_items.extend(cset['expression_items'])
        flat_member_items.extend(cset['member_items'])

    if return_type == 'flat':
        return {'cset_containers': cset_containers, 'cset_versions': cset_versions,
                'expression_items': flat_expression_items, 'member_items': flat_member_items}
    return {'cset_containers': cset_containers, 'cset_versions': cset_versions_with_concepts}


def fetch_object_by_id(object_name: str, id_field: str, object_id: int) -> Dict:
    """Fetch object by its id"""
    query_params = [get_query_param(id_field, 'eq', str(object_id))]
    matches: List[Dict] = make_objects_request(object_name, query_params=query_params, return_type='data')
    obj: Dict = matches[0]['properties']
    return obj


def fetch_cset_version(object_id: int) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OMOPConceptSet', 'codesetId', object_id)


def fetch_cset_container(object_id: int) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OMOPConceptSetContainer', 'conceptSetId', object_id)


def fetch_cset_member_item(object_id: int) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OMOPConcept', 'conceptId', object_id)


def fetch_cset_expression_item(object_id: int) -> Dict:
    """Get object from enclave"""
    return fetch_object_by_id('OmopConceptSetVersionItem', 'itemId', object_id)


def fetch_object_and_add_to_db(con: Connection, table: str, object_name: str, object_id: int):
    """Fetch object and add to db"""
    obj = fetch_cset_version(object_id)
    table_obj = convert_row(object_name, table, obj)
    insert_from_dict(con, table, table_obj)


def concept_expression_enclave_to_db(con: Connection, object_id: int):
    """Given ID, get object's current state from the enclave, and add it the DB"""
    fetch_object_and_add_to_db(con, 'concept_set_version_item', 'OmopConceptSetVersionItem', object_id)


def concept_member_enclave_to_db(con: Connection, object_id: int):
    """Given ID, get object's current state from the enclave, and add it the DB"""
    fetch_object_and_add_to_db(con, 'concept_set_members', 'OMOPConcept', object_id)


def cset_container_enclave_to_db(con: Connection, object_id: int):
    """Given ID, get object's current state from the enclave, and add it the DB"""
    fetch_object_and_add_to_db(con, 'concept_set_container', 'OMOPConceptSetContainer', object_id)


def cset_version_enclave_to_db(con: Connection, object_id: int):
    """Given ID, get object's current state from the enclave, and add it the DB"""
    fetch_object_and_add_to_db(con, 'code_sets', 'OMOPConceptSet', object_id)


def items_to_atlas_json_format(items):
    """Convert version items to atlas json format"""
    flags = ['includeDescendants', 'includeMapped', 'isExcluded']
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
def get_codeset_json(codeset_id, con=get_db_connection(), use_cache=True, set_cache=True) -> Dict:
    if use_cache:
        jsn = sql_query_single_col(con, f"""
            SELECT json
            FROM concept_set_json
            WHERE codeset_id = {int(codeset_id)}
        """)
        if jsn:
            return jsn[0]
    cset = make_objects_request(f'objects/OMOPConceptSet/{codeset_id}', return_type='data', expect_single_item=True)
    container = make_objects_request(
        f'objects/OMOPConceptSetContainer/{quote(cset["conceptSetNameOMOP"], safe="")}',
        return_type='data', expect_single_item=True)
    items = get_expression_items(codeset_id)
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
            run_sql(con, f"""
                INSERT INTO concept_set_json VALUES (
                    {codeset_id},
                    (:jsn)::json
                )
            """, {'jsn': sql_jsn})
        except Exception as err:
            print('trying to insert\n')
            print(sql_jsn)
            raise err
    return jsn


# todo: split into get/update
def get_n3c_recommended_csets(save=False):
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


def cli():
    """Command line interface for package."""
    raise "We aren't using this as of 2023-02. Leaving in place in case we want to use again."
    # package_description = 'Tool for working w/ the Palantir Foundry enclave API. ' \
    #                       'This part is for downloading enclave datasets.'
    # parser = ArgumentParser(description=package_description)
    #
    # # parser.add_argument(
    # #     '-a', '--auth_token_env_var',
    # #     default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
    # #     help='Name of the environment variable holding the auth token you want to use')
    # # todo: 'objects' alone doesn't make sense because requires param `object_type`
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


# todo: @Siggie: is this redundant with get_concept_set_version_expression_items() below?
def get_expression_items(codeset_id) -> List[Dict]:
    """Get expression items"""
    _items = make_objects_request(
        f'objects/OMOPConceptSet/{codeset_id}/links/omopConceptSetVersionItem',
        handle_paginated=True, return_type='data'
    )
    items = [i['properties'] for i in _items]
    return items


def get_concept_set_version_expression_items(
    version_id: Union[str, int], return_detail=['id', 'full'][0]
) -> List[Dict]:
    """Get concept set version expression items"""
    version_id = str(version_id)
    response: Response = get_object_links(
        object_type='OMOPConceptSet',
        object_id=version_id,
        link_type='omopConceptSetVersionItem')
    if return_detail == 'id':
        return [x['properties']['itemId'] for x in response.json()['data']]
    return [x for x in response.json()['data']]


def get_concept_set_version_members(version_id: Union[str, int], return_detail=['id', 'full'][0]) -> List[Dict]:
    """Get concept set members"""
    version_id = str(version_id)
    response: Response = get_object_links(
        object_type='OMOPConceptSet',
        object_id=version_id,
        link_type='omopconcepts')
    if return_detail == 'id':
        return [x['properties']['conceptId'] for x in response.json()['data']]
    return [x for x in response.json()['data']]


def get_researchers(verbose=False) -> List[Dict]:
    """Get researcher objects
    Researcher exploration page:
    https://unite.nih.gov/workspace/hubble/exploration?objectTypeRid=ri.ontology.main.object-type.70d7defa-4914-422f-83da-f45c28befd5a
    """
    object_name = 'Researcher'
    data: List[Dict] = make_objects_request(object_name, handle_paginated=True, return_type='data', verbose=verbose)
    return data


def get_projects(verbose=False) -> List[Dict]:
    """Get project objects
    Projects exploration page:
    https://unite.nih.gov/workspace/hubble/exploration?objectTypeRid=ri.ontology.main.object-type.84d08d30-bbea-4e3d-a995-040057391a71
    """
    object_name = 'ResearchProject'
    data: List[Dict] = make_objects_request(object_name, handle_paginated=True, return_type='data', verbose=verbose)
    return data


if __name__ == '__main__':
    ot = get_object_types()
    get_n3c_recommended_csets(save=True)
