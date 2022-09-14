"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
- jq docs: https://stedolan.github.io/jq/manual/
- jq python api docs: https://github.com/mwilliamson/jq.py
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
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pandasql import sqldf
from pydantic import BaseModel

from enclave_wrangler.config import config, FAVORITE_DATASETS

import jq


DEBUG = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent
OBJECTS_PATH = f'{PROJECT_DIR}/termhub-csets/objects'
CSETS_JSON_PATH = f'{OBJECTS_PATH}/OMOPConceptSet/latest.json'
CONCEPTS_JSON_PATH = f'{OBJECTS_PATH}/OMOPConcept/latest.json'
CONCEPT_SET_VERSION_ITEM_JSON_PATH = f'{OBJECTS_PATH}/OmopConceptSetVersionItem/latest.json'
CSV_PATH = f'{PROJECT_DIR}/termhub-csets/datasets'

API_NAME_TO_DATASET_NAME = {        # made this lookup, but then didn't need it
                                    # keep if need later?
    'OMOPConcept':               'concept',
    'OMOPConceptSet':            'concept_set_members',
    'OMOPConceptSetContainer':   'concept_set_version_item',
    'OmopConceptSetVersionItem': 'concept_relationship',
}

# load big files!
# TODO: this is too slow for development where the backend has to restart all the time
#  @Joe: would it be too crazy to run 2 backend servers, 1 to hold the data and 1 to service requests / logic? probably.
#  @Siggie: Not a bad idea. If we invest time in that, may be better to do RDBMS instead, but I think running 2
#   *might* not take too much time... actually maybe it would. Need to pass data between the processes. RCP? We could
#   do it over REST, but idk. Maybe worth looking into / trying for an hour.

# TODO: #2: remove try/except when download datasets
try:

    # code_set.version got mangled into version numbers like 1.0, 2.0
    #  TODO: try to fix.... not working yet:
    #
    # converters = {
    #     'int': lambda v: v.astype(int)
    # }
    # def bool_converter(v):
    #     return v and True or False
    #
    # csv_opts = {
    #     # 'code_sets': {'dtype': {'version': int}}
    #     'code_sets': {'converters': {'version': converters['int']}}
    # }
    #
    # df = pd.read_csv(os.path.join(CSV_PATH, 'code_sets' + '.csv'), **(csv_opts['code_sets']))

    DS = {name: pd.read_csv(os.path.join(CSV_PATH, name + '.csv'), keep_default_na=False) for name in FAVORITE_DATASETS}
    #  TODO: Fix this warning?
    #   DtypeWarning: Columns (4) have mixed types. Specify dtype option on import or set low_memory=False.
    #   keep_default_na fixes some or all the warnings, but doesn't manage dtypes well.
    #   did this in termhub-csets/datasets/fixing-and-paring-down-csv-files.ipynb:
    #   csm = pd.read_csv('./concept_set_members.csv',
    #                    # dtype={'archived': bool},    # doesn't work because of missing values
    #                   converters={'archived': lambda x: x and True or False}, # this makes it a bool field
    #                   keep_default_na=False)
    print(f'Favorite datasets loaded: {DS.keys()}')
    CONCEPT = DS['concept']
    # PYSQLDF = lambda q: sqldf(q, globals()) # I think you need to call this in the function you're using it in
    # COUNTS = PYSQLDF("""
    #     SELECT vocabulary_id, COUNT(*) AS cnt
    #     FROM CONCEPT
    #     GROUP BY 1""")
except FileNotFoundError:
    print('Datasets not loaded.')

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)


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
    with open(jpath, 'r') as f:
        d = json.load(f)
        return d
    return {'Error': f'failure in load_json({objtype}'}


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}

# Routes
@APP.get("/concept-set-names")
@APP.get("/datasets/csets/names")
@APP.get("/jq-cset-names")
def cset_names() -> Union[Dict, List]:
    """Get concept set names"""
    return csets_read(field_filter=['concept_set_name'])


@APP.get("/cset-versions")
def csetVersions() -> Union[Dict, List]:
    csm = DS['code_sets']
    # todo: would be nicer to do this in a cleaner, shorter way, e.g.:
    # g = csm[['concept_set_name', 'codeset_id', 'version']].groupby('concept_set_name').agg(dict)
    g: Dict[List[Dict[str, int]]] = {}
    concept_set_names = list(csm['concept_set_name'].unique())
    for cs_name in concept_set_names:
        csm_i = csm[csm['concept_set_name'] == cs_name]
        for _index, row in csm_i.iterrows():
            version: int = int(float(row['version'])) if row['version'] else None
            codeset_id: int = row['codeset_id']
            if not version:
                continue
            if cs_name not in g:
                g[cs_name] = []
            g[cs_name].append({'version': version, 'codeset_id': codeset_id})

    return g


def jqQuery(objtype: str, query: str, objlist=None, ) -> Union[Dict, List]:
    objlist = objlist or load_json(objtype)
    if DEBUG:
        jpath = json_path(objtype)
        cmd = f"jq '{query}' {jpath}"
        print(f'jq cmd:\n{cmd}')

    result = jq.compile(query).input(objlist).all()
    return result


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


@APP.get("/concept-sets-with-concepts")
def concept_sets_with_concepts(
    codeset_id: Union[str, None] = Query(default=[]),
    field: Union[List[str], None] = Query(default=[]),
    concept_field_filter: Union[List[str], None] = Query(default=None),
) -> Union[Dict, List]:
    """Returns list of concept sets selected and their concepts

    sample url:
        http://127.0.0.1:8000/concept-sets-with-concepts?concept_field_filter=conceptId&concept_field_filter=conceptName&codeset_id=614602276&codeset_id=490710207&codeset_id=394464897&codeset_id=13193785
        
    If no codeset_id, doesn't return concepts; just concept_sets.
        TODO: is that still true?

    Switched to using pandas (not pandasql) not sure if it works like it should -- well
        something's going wrong in json conversion, hitting error when returning. End of
        stacktrace is:
          File "/opt/homebrew/Cellar/python@3.10/3.10.5/Frameworks/Python.framework/Versions/3.10/lib/python3.10/json/encoder.py", line 257, in iterencode
            return _iterencode(o, 0)
        ValueError: Out of range float values are not JSON compliant
    @joeflack4 can you take a look? thanks!

    """

    # if codeset_id empty, [] otherwise split and convert to int
    codeset_ids = codeset_id and [int(cid) for cid in codeset_id.split('|')] or []

    # TODO: switch to using pandasql
    print(f'Favorite datasets loaded: {DS.keys()}')
    sql = lambda q: sqldf(q, globals())

    # ds_name = API_NAME_TO_DATASET_NAME[objtype]
    # cdf = DS['concept']
    csm = DS['concept_set_members']
    # container = DS['concept_set_container_edited']
    codeset = DS['code_sets']

    # using pandasql seems to be MUCH slower than regular pandas:
    # csets = sql(f"""
    #     SELECT concept_id
    #     FROM csm
    #     WHERE codeset_id IN (23007370, 23600781)
    # """)
    csm = csm[csm.codeset_id.isin(codeset_ids)]
    codeset = codeset[codeset.codeset_id.isin(codeset_ids)]
    csets = codeset.to_dict(orient='records')
    for cset in csets:
        cset['concepts'] = csm[csm.codeset_id == cset['codeset_id']].to_dict(orient='records')

        # del csets[0]['Unnamed: 0']

    # don't think we need this anymore. TODO: delete when sure
    # concept_sets = fields_from_objlist(objtype='OMOPConceptSet', filter=[f'codeset_id:{codeset_id}'], field=field)
    # if not codeset_id:
    #     return concept_sets
    # else:
    #     # Mutate `concept_sets` by adding `concepts` field
    #     concept_sets_lookup = {x['codeset_id']: x for x in concept_sets}
    #     concept_id_concepts_map = concepts_read(
    #         concept_set_id=[x['codeset_id'] for x in concept_sets], field_filter=concept_field_filter)
    #     for cs_id, cs in concept_sets_lookup.items():
    #         if cs_id in concept_id_concepts_map:
    #             cs['concepts'] = concept_id_concepts_map[cs_id]
    #         else:
    #             cs['concepts'] = {}
    #
    #
    #     # TODO: Remove this block after we get all the data. This just fills in missing data for easy frontend rendering
    #     for cs in concept_sets:
    #         for concept_id, concept_props in cs['concepts'].items():
    #             if not concept_props:
    #                 cs['concepts'][concept_id] = {
    #                     **{'concept_id': concept_id},
    #                     **{f: '<Data not yet downloaded>' for f in concept_field_filter if f != 'concept_id'}}
    # print(json.dumps(concept_sets, indent=2)[0:400])
    # print(json.dumps(csets, indent=2)[0:400])
    return csets
    # return concept_sets


# TODO:
@APP.get("/concept-sets-page")
def concept_sets_page():
    """Everything that the concept set page needs to in 1 single request, ideally."""
    # todo: cache and update it when newer source datasets are detected
    pass


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


# TODO: Maybe change to `id` instead of row index
@APP.put("/datasets/csets")
def csets_update(d: CsetsUpdate = None) -> Dict:
    """Update cset dataset. Works only on tabular files."""
    # Vars
    result = 'success'
    details = ''
    cset_dir = os.path.join(PROJECT_DIR, 'termhub-csets')
    path_root = os.path.join(cset_dir, 'datasets')

    # Update cset
    # todo: dtypes need to be registered somewhere. perhaps a <CSV_NAME>_codebook.json()?, accessed based on filename,
    #  and inserted here
    # todo: check git status first to ensure clean? maybe doesn't matter since we can just add by filename
    path = os.path.join(path_root, d.dataset_path)
    # noinspection PyBroadException
    try:
        df = pd.read_csv(path, dtype={'id': np.int32, 'last_name': str, 'first_name': str}).fillna('')
        for index, field_values in d.row_index_data_map.items():
            for field, value in field_values.items():
                df.at[index, field] = value
        df.to_csv(path, index=False)
    except BaseException as err:
        result = 'failure'
        details = str(err)

    # Push commit
    # todo?: Correct git status after change should show something like this near end: `modified: FILENAME`
    relative_path = os.path.join('datasets', d.dataset_path)
    # todo: Want to see result as string? only getting int: 1 / 0
    #  ...answer: it's being printed to stderr and stdout. I remember there's some way to pipe and capture if needed
    # TODO: What if the update resulted in no changes? e.g. changed values were same?
    git_add_result = sp_call(f'git add {relative_path}'.split(), cwd=cset_dir)
    if git_add_result != 0:
        result = 'failure'
        details = f'Error: Git add: {d.dataset_path}'
    git_commit_result = sp_call(['git', 'commit', '-m', f'Updated by server: {relative_path}'], cwd=cset_dir)
    if git_commit_result != 0:
        result = 'failure'
        details = f'Error: Git commit: {d.dataset_path}'
    git_push_result = sp_call('git push origin HEAD:main'.split(), cwd=cset_dir)
    if git_push_result != 0:
        result = 'failure'
        details = f'Error: Git push: {d.dataset_path}'

    return {'result': result, 'details': details}

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
        # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        "authorization": f"Bearer {config['PERSONAL_ENCLAVE_TOKEN']}",
        # 'content-type': 'application/json'
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


@APP.get("/ontocallOBSOLETE")   # TODO: still using ontocall anywhere? time to get rid of it?
def ontocall(path) -> [{}]:
    """API documentation at
    https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
    https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        "authorization": f"Bearer {config['PERSONAL_ENCLAVE_TOKEN']}",
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


@APP.get("linkTypesForObjectTypes")
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
        "authorization": f"Bearer {config['PERSONAL_ENCLAVE_TOKEN']}",
        # 'content-type': 'application/json'
    }
    # ontology_rid = config['ONTOLOGY_RID']
    data = {
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                "00000001-9834-2acf-8327-ecb491e69b5c"
        }
    }
    api_path = '/ontology-metadata/api/ontology/linkTypesForObjectTypes'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    response = requests.post(url, headers=headers, data=data)
    response_json = response.json()
    return response_json


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
