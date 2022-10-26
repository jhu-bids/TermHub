"""Temporary routes for trying stuff out. will merge into backend.py

TODO's
  1. Joe will rewrite enclave_api.py, and then we can connect backend.py with that. At around that point, we should no
  longer need 'reviving_ontology_api_stuff.py' when that is working correctly.

# other api calls might be handy:
#   concepts for concept set:
#       http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/729489911/links/omopconcepts
#   concepts for concept set:
#       http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/729489911/links/omopconcepts
#   linktypes:
#       http://127.0.0.1:8000/linkTypesForObjectTypes
"""
import json
import os
import errno
from pathlib import Path
from subprocess import call as sp_call
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
# from pandasql import sqldf
from pydantic import BaseModel
from enclave_wrangler.config import config, FAVORITE_DATASETS
import jq


DEBUG = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent
OBJECTS_PATH = f'{PROJECT_DIR}/termhub-csets/objects'
CSETS_JSON_PATH = f'{OBJECTS_PATH}/OMOPConceptSet/latest.json'
CONCEPTS_JSON_PATH = f'{OBJECTS_PATH}/OMOPConcept/latest.json'
CONCEPT_SET_VERSION_ITEM_JSON_PATH = f'{OBJECTS_PATH}/OmopConceptSetVersionItem/latest.json'

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)


@APP.get("/passthru-post")
def passthruPost(path, data) -> [{}]:
    """API documentation at
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
    https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        # "authorization": f"Bearer {config['OTHER_TOKEN']}",
    }
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    print(f'passthru: {api_path}\n{url}')

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        response_json: Dict = response.json()
        return response_json
    except BaseException as err:
        print(f"Unexpected {type(err)}: {str(err)}")
        return {'ERROR': str(err)}


# Utils
def json_path(objtype: str) -> str:
    """ construct path for json file given an object type name, e.g., OMOPConceptSet """
    jdir = f'{OBJECTS_PATH}/{objtype}'
    if os.path.isdir(jdir):
        jpath = f'{jdir}/latest.json'
        if os.path.isfile(jpath):
            return jpath
        else:
            # from https://stackoverflow.com/a/36077407/1368860
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), jpath)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), jdir)


def load_json(objtype: str) -> List[Dict]:
    """ load json file given an object type name, e.g., OMOPConceptSet """
    jpath = json_path(objtype)
    try:
        with open(jpath, 'r') as f:
            d = json.load(f)
            return d
    except Exception:
        return [{'Error': f'failure in load_json({objtype}'}]


def jqQuery(objtype: str, query: str, objlist=None, ) -> Union[Dict, List]:
    objlist = objlist or load_json(objtype)
    if DEBUG:
        jpath = json_path(objtype)
        cmd = f"jq '{query}' {jpath}"
        print(f'jq cmd:\n{cmd}')

    result = jq.compile(query).input(objlist).all()
    return result


def validFieldList(objlist: List[Dict], fields: List[str]):
    """ helper for fields_from_objlist"""
    all_fields = jq.compile('.[0] | keys').input(objlist).first()
    ok_fields = [f for f in fields if f in all_fields]
    return ok_fields


@APP.get("/datasets/csets")
def csets_read(
    field_filter: Union[List[str], None] = Query(default=None), path=CSETS_JSON_PATH
    # value_filter: Union[List[str], None] = Query(default=None) # not implemented here
) -> Union[Dict, List]:
    """Get concept sets

    field_filter: If present, the data returned will only contain these fields. Example: Passing `concept_set_name` as
    the only field_filter for OMOPConceptSet will return a string list of concept set names.

    Resources: jq docs: https://stedolan.github.io/jq/manual/ , jq python api doc: https://github.com/mwilliamson/jq.py
    """
    if field_filter:
        if len(field_filter) > 1:
            d = {'error': 'Currently only 1 field_filter is allowed.'}
        else:
            # TODO: Need to replace this with Python API. Otherwise, deployment will be harder and must global
            #  installation of JQ.
            #  DONE

            query = f".[] | .{field_filter[0]}"
            cmd = f"jq '{query}' {path}"
            print(f'jq cmd:\n{cmd}')

            with open(path, 'r') as f:
                d = json.load(f)
                result = jq.compile(query).input(d).all()
                return result

            # output, err = jq_wrapper(query)
            # if err:
            #     return {'error': str('error')}
            # d = output.split('\n')
            # # x[1:-1]: What gets returned is a \n-delimited string of names, where each name is formatted
            # # as '"{NAME}"',so we need to remove the extra set of quotations.
            # # TODO: This operation likely needs to be done in a variety of cases, but I don't know JQ well enough to
            # #  anticipate all of the situations where this might arise. - joeflack4 2022/08/24
            # # todo: Is this List[str] preferable to List[Dict,? e.g. [{'concept_set_name': 'HEART FAILURE'}, ...]?
            # d = [x[1:-1] for x in d]
            # return d
    else:
        with open(path, 'r') as f:
            d = json.load(f)
    return d


# # todo: @Siggie: Not sure how to do what I needed in JQ, so no JQ in here yet
# @APP.get("/datasets/concepts")
# def concepts_read(
#     field_filter: Union[List[str], None] = Query(default=None),
#     concept_set_id: Union[List[int], None] = Query(default=None), path=CONCEPTS_JSON_PATH,
# ) -> Union[Dict, List]:
#     """Get concept sets
#
#     field_filter: If present, the data returned will only contain these fields. Example: Passing `concept_name` as
#     the only field_filter for OMOPConcept will return a string list of concept names.
#     concept_set_id: Only include concepts w/ these IDs. Returned data will be like {concept_set_id: <data>}
#
#     Resources: jq docs: https://stedolan.github.io/jq/manual/ , jq python api doc: https://github.com/mwilliamson/jq.py
#     """
#     with open(path, 'r') as f:
#         concepts: Union[List, Dict] = json.load(f)
#     with open(CONCEPT_SET_VERSION_ITEM_JSON_PATH, 'r') as f:
#         concept_set_items: List[Dict] = json.load(f)
#
#     # I feel like this could be done in less lines - Joe 2022/09/07
#     if concept_set_id:
#         # concept_set_items: For codeset_id->concept_id mapping
#         concept_set_items2 = [d for d in concept_set_items if d['codeset_id'] in concept_set_id]
#         concept_lookup = {d['concept_id']: d for d in concepts}
#
#         concept_set_concepts: Dict[int, Dict] = {}
#         for item in concept_set_items2:
#             cs_id: int = item['codeset_id']
#             c_id: int = item['concept_id']
#             if cs_id not in concept_set_concepts:
#                 concept_set_concepts[cs_id] = {}
#             concept_set_concepts[cs_id][c_id] = concept_lookup.get(c_id, {})
#
#         concepts = concept_set_concepts
#         if field_filter:
#             concept_set_concepts_new = {}
#             for cset_id, concept_dicts in concept_set_concepts.items():
#                 new_cset = {}
#                 for concept_id, concept_dict in concept_dicts.items():
#                     new_dict = {k: v for k, v in concept_dict.items() if k in field_filter}
#                     new_cset[concept_id] = new_dict
#                 concept_set_concepts_new[cset_id] = new_cset
#             concepts = concept_set_concepts_new
#
#     elif field_filter:
#         pass  # TODO
#
#     return concepts


@APP.middleware("http")
async def catch_all(request: Request, call_next):
    print('called backend with url', request.url)
    response = await call_next(request)
    return response


@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list
    # return {"try": "/ontocall?path=<enclave path after '/api/v1/ontologies/'>",
    #         "example": "/ontocall?path=objects/list-objects/"}
    # return ontocall('objectTypes')


@APP.get("/passthru")
def passthru(path) -> [{}]:
    """API documentation at
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
    https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        # "authorization": f"Bearer {config['OTHER_TOKEN']}",
    }
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    print(f'passthru: {api_path}\n{url}')

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json: Dict = response.json()
        return response_json
    except BaseException as err:
        print(f"Unexpected {type(err)}: {str(err)}")
        return {'ERROR': str(err)}


@APP.get("/ontocall")   # TODO: still using ontocall anywhere? time to get rid of it?
def ontocall(path) -> [{}]:
    """API documentation at
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
    https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        "authorization": f"Bearer {config['OTHER_TOKEN']}",
        # 'content-type': 'application/json'
    }
    # return {'path': path}
    print(f'ontocall param: {path}\n')
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    print(f'ontocall: {api_path}\n{url}')

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json: Dict = response.json()
        if 'data' in response_json:
            data = response_json['data']
        else:
            data = response_json
        if 'properties' in data:
            data = data['properties']  # e.g., http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/729489911
            data['rid'] = response_json['rid']
    except BaseException as err:
        print(f"Unexpected {type(err)}: {str(err)}")
        return {'ERROR': str(err)}

    return data

    # TODO: @siggie: This code was unreachable because of `return data` above, so i commented out
    # if path == 'objectTypes':
    #     # data = json['data']
    #     print(data)
    #     return data
    #     api_names = sorted([
    #         t['apiName'] for t in data if t['apiName'].startswith('OMOP')])
    #     return api_names
    # if os.path.startswith('objectTypes/'):
    #     return json
    # return {'valid but unhandled path': path, 'json': json}


@APP.put("/datasets/vocab")
def vocab_update():
    """Update vocab dataset"""
    pass


@APP.get("/linkTypesForObjectTypes")
def link_types() -> List[Dict]:
    """
    TODO: write this api call?
    TODO: curl below gets json for
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
    # ontology_rid = config['ONTOLOGY_RID']
    data = json.dumps({
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                "00000001-9834-2acf-8327-ecb491e69b5c"
        }
    })
    api_path = '/ontology-metadata/api/ontology/linkTypesForObjectTypes'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    response = requests.post(url, headers=headers, data=data)
    response_json = response.json()
    return response_json


# @APP.get("/fields-from-objlist")
# def fields_from_objlist(
#     objtype: str = Query(...),
#     filter: Union[List[str], None] = Query(default=[]),
#     field: Union[List[str], None] = Query(default=[]),
# ) -> Union[Dict, List]:
#     """
#         get one or more fields from specified object type, example:
#         http://127.0.0.1:8000/fields-from-objlist?field=concept_set_name&field=codeset_id&objtype=OMOPConceptSet
#     """
#
#     queryClauses = []
#     objlist = load_json(objtype)
#     fields = validFieldList(objlist=objlist, fields=field)
#     if len(fields):
#         queryClauses.append('{' + ', '.join(fields) + '}')
#
#     valFilters = {k: v and v.split('|') or [] for k, v in [filt.split(':') for filt in filter]}
#     filterFields = validFieldList(objlist=objlist, fields=valFilters.keys())
#     for filterField in filterFields:
#         filtVals = valFilters[filterField]
#         if len(filtVals):
#             condition = 'or'.join([f' .codeset_id == {val} ' for val in filtVals])
#             clause = f'select({condition})'
#             queryClauses.insert(0, clause)
#
#     queryClauses.insert(0, '.[]')
#     query = ' | '.join(queryClauses)
#     subset = jqQuery(objtype=objtype, objlist=objlist, query=query)
#
#     return subset
#     # groupQuery = 'group_by(.concept_set_name) | map({ key: .[0].concept_set_name | tostring, value: [.[] | {version, codeset_id}] }) | from_entries'
#     # res = jqQuery(objtype=objtype, objlist=subset, query=groupQuery)
#     # return res


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
