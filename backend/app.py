"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
import os
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Union
from functools import cache

import numpy as np
import pandas as pd
import uvicorn
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from sqlalchemy.engine import LegacyRow, RowMapping
from subprocess import call as sp_call

from backend.db.queries import get_all_parent_children_map
from backend.utils import JSON_TYPE
from enclave_wrangler.dataset_upload import upload_new_container_with_concepts, \
    upload_new_cset_container_with_concepts_from_csv, upload_new_cset_version_with_concepts, \
    upload_new_cset_version_with_concepts_from_csv
from enclave_wrangler.utils import make_objects_request
from enclave_wrangler.config import RESEARCHER_COLS

from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col


PROJECT_DIR = Path(os.path.dirname(__file__)).parent
# CON: using a global connection object is probably a terrible idea, but shouldn't matter much until there are multiple
# users on the same server
APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)
CON = get_db_connection()
CACHE = {
    'all_parent_children_map': get_all_parent_children_map(CON)
}


# Utility functions ----------------------------------------------------------------------------------------------------
@cache
def parse_codeset_ids(qstring) -> List[int]:
    """Parse codeset_ids which are a | delimited string"""
    if not qstring:
        return []
    requested_codeset_ids = qstring.split('|')
    requested_codeset_ids = [int(x) for x in requested_codeset_ids]
    return requested_codeset_ids


@cache
def get_container(concept_set_name):
    """This is for getting the RID of a dataset. This is available via the ontology API, not the dataset API.
    TODO: This needs caching, but the @cache decorator is not working."""
    return make_objects_request(f'objects/OMOPConceptSetContainer/{urllib.parse.quote(concept_set_name)}')


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


# Database functions ---------------------------------------------------------------------------------------------------
def get_concept_set_member_ids(
    codeset_ids: List[int], columns: Union[List[str], None] = None, column: Union[str, None] = None, con=CON
) -> Union[List[int], List[LegacyRow]]:
    """Get concept set members"""
    if column:
        columns = [column]
    if not columns:
        columns = ['codeset_id', 'concept_id']

    # should check that column names are valid columns in concept_set_members
    query = f"""
        SELECT DISTINCT {', '.join(columns)}
        FROM concept_set_members csm
        WHERE csm.codeset_id = ANY(:codeset_ids)
    """
    res: List[LegacyRow] = sql_query(con, query, {'codeset_ids': codeset_ids}, debug=False)
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        res: List[int] = [r[0] for r in res]
    return res


# TODO
#  i. Keys in our old `get_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'rid', 'selected', 'created_at_container', 'created_at_version'
#   , 'intention_container', 'researchers', 'intention_version', 'created_by_container', 'intersecting_concepts',
#   'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `get_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention',
#   'container_status', 'container_created_by']
#  fixes:
#       probably don't need precision etc.
#       switched _container suffix on duplicate col names to container_ prefix
#       joined OMOPConceptSet in the all_csets ddl to get `rid`
def get_csets(codeset_ids: List[int], con=CON) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    rows: List[LegacyRow] = sql_query(
        con, """
          SELECT *
          FROM all_csets
          WHERE codeset_id = ANY(:codeset_ids);""",
        {'codeset_ids': codeset_ids})
    # {'codeset_ids': ','.join([str(id) for id in requested_codeset_ids])})
    row_dicts = [dict(x) for x in rows]
    for row in row_dicts:
        row['researchers'] = get_row_researcher_ids_dict(row)

    return row_dicts


def get_row_researcher_ids_dict(row: Dict):
    """
        dict of id: [roles]
        was: {role1: id1, role2: id2, role3: id2} # return {col: row[col] for col in RESEARCHER_COLS if row[col]}
        switched to {id1: [role1], id2: [role2, role3]}
    """
    roles = {}
    for col in RESEARCHER_COLS:
        role = row[col]
        if not role:
            continue
        if not role in roles:
            roles[row[col]] = []
        roles[row[col]].append(col)
    return roles


def get_all_researcher_ids(rows: List[Dict]):
    return set([r[c] for r in rows for c in RESEARCHER_COLS if r[c]])


def get_researchers(ids: List[str], fields: List[str] = None) -> JSON_TYPE:
    """Get researcher info for list of multipassIds.
    fields is the list of fields to return from researcher table; defaults to * if None."""
    if fields:
        fields = ', '.join([f'"{x}"' for x in fields])
    else:
        fields = '*'

    query = f"""
        SELECT {fields}
        FROM researcher
        WHERE "multipassId" = ANY(:id)
    """
    res: List[RowMapping] = sql_query(CON, query, {'id': list(ids)}, return_with_keys=True)
    res2 = {r['multipassId']: dict(r) for r in res}
    for id in ids:
        if id not in res2:
            res2[id] = {"multipassId": id, "name": "unknown", "emailAddress": id}
    return res2


def get_concepts(concept_ids: List[int], con=CON) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    rows: List[LegacyRow] = sql_query(
        con, """
          SELECT *
          FROM concepts_with_counts
          WHERE concept_id = ANY(:concept_ids);""",
        {'concept_ids': concept_ids})
    return rows


# TODO
#  i. Keys in our old `related_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'selected', 'created_at_container', 'created_at_version', 'intention_container', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `related_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention', 'container_status', 'container_created_by']
#  see fixes above. i think everything here is fixed now
def get_related_csets(codeset_ids: List[int] = None, selected_concept_ids: List[int] = None, con=CON) -> List[Dict]:
    """Get information about concept sets related to those selected by user"""
    if codeset_ids and not selected_concept_ids:
        selected_concept_ids = get_concept_set_member_ids(codeset_ids, column='concept_id')
    query = """
    SELECT DISTINCT codeset_id
    FROM concept_set_members
    WHERE concept_id = ANY(:concept_ids)
    """
    related_codeset_ids = sql_query_single_col(con, query, {'concept_ids': selected_concept_ids}, )
    related_csets = get_csets(related_codeset_ids)
    selected_cids = set(selected_concept_ids)
    selected_cid_cnt = len(selected_concept_ids)
    # this loop takes some time
    for cset in related_csets:
        cids = get_concept_set_member_ids([cset['codeset_id']], column='concept_id')
        intersecting_concepts = set(cids).intersection(selected_cids)
        cset['intersecting_concepts'] = len(intersecting_concepts)
        cset['recall'] = cset['intersecting_concepts'] / selected_cid_cnt
        cset['precision'] = cset['intersecting_concepts'] / len(cids)
        cset['selected'] = cset['codeset_id'] in codeset_ids
    return related_csets


def get_cset_members_items(codeset_ids: List[int] = None, con=CON) -> List[LegacyRow]:
    """Get concept set members items for selected concept sets
        returns:
        ...
        item: True if its an expression item, else false
        csm: false if not in concept set members
    """
    return sql_query(
        con, f""" 
        SELECT *
        FROM cset_members_items
        WHERE codeset_id = ANY(:codeset_ids)
        """,
        {'codeset_ids': codeset_ids})

def new_hierarchy(root_cids: List[int], cids: List[int], con=CON) -> Dict:
    q = sql_query(
        con, f""" 
        SELECT *
        FROM concept_ancestor
        WHERE ancestor_concept_id = ANY(:root_cids)
          AND descendant_concept_id = ANY(:cids)
          AND min_levels_of_separation > 0
        ORDER BY ancestor_concept_id, min_levels_of_separation
        """,
        {'root_cids': root_cids, 'cids': cids})
    return q

def hierarchy(codeset_ids: List[int] = None, selected_concept_ids: List[int] = None) -> Dict:
    """Get hierarchy of concepts in selected concept sets"""
    if not selected_concept_ids:
        selected_concept_ids = get_concept_set_member_ids(codeset_ids, column='concept_id')

    # selected_roots: List[int] = top_level_cids(selected_concept_ids)
    added_count: Dict[int, int] = {}

    def recurse(ids):
        """Recurse"""
        x = {}
        for i in ids:
            children = CACHE['all_parent_children_map'].get(i, [])
            x[i] = recurse(children)
            added_count[i] = added_count.get(i, 0) + 1
        return x

    # d = recurse(selected_roots)
    d = recurse(selected_concept_ids)
    
    # remove duplicate trees at root
    for _id, count in added_count.items():
        if count > 1:
            try:
                del d[_id]
            except KeyError:
                pass

    # todo: this reverts new way of indicating 'no children' back to null. any more seemly way to do?
    d2 = json.dumps(d)
    d2 = d2.replace('{}', 'null')
    d3 = json.loads(d2)

    return d3


junk = """  -- retaining hierarchical query (that's not working, for possible future reference)
-- example used in http://127.0.0.1:8080/backend/old_cr-hierarchy_samples/cr-hierarchy-example1.json 
-- 411456218|40061425|484619125|419757429       -- 40061425 doesn't seem to exist
-- 411456218,40061425,484619125,419757429
WITH RECURSIVE hier(concept_id_1, concept_id_2, path, depth) AS (
    SELECT concept_id_1,
          concept_id_2,
          CAST(concept_id_1 AS text) || '-->' || CAST(concept_id_2 AS text) AS path,
          0 AS depth
    FROM concept_relationship
    WHERE concept_id_1 IN ( -- top level cids for 8 codeset_ids above
        45946655, 3120383, 3124992, 40545247, 3091356, 3099596, 3124987, 40297860, 40345759, 45929656, 3115991, 40595784, 44808268, 3164757, 40545248, 45909769,
        45936903, 40545669, 45921434, 45917166, 4110177, 3141624, 40316548, 44808238, 4169883, 45945309, 3124228, 40395876, 3151089, 40316547, 40563017, 44793048
        -- ...
    )
    UNION
    SELECT cr.concept_id_1,
            cr.concept_id_2,
            hier.path || '-->' || CAST(cr.concept_id_2 AS text) AS path,
            hier.depth + 1
    FROM concept_relationship cr
    JOIN hier ON cr.concept_id_1 = hier.concept_id_2
    WHERE hier.depth < 2
)
SELECT DISTINCT path, depth
FROM hier
ORDER BY path;
"""


def child_cids(concept_id: int, con=CON) -> List[Dict]:
    """Get child concept ids"""
    # selected_concept_ids = get_concept_set_member_ids([concept_id])
    child_cids = sql_query_single_col(
        con, f""" 
        SELECT DISTINCT concept_id_2
        FROM concept_relationship cr
        WHERE cr.concept_id_1 = ANY(:concept_ids)
          AND cr.relationship_id = 'Subsumes'
        """,
        {'concept_id': concept_id})
    return child_cids


def get_all_csets(con=CON) -> Union[Dict, List]:
    """Get all concept sets"""
    # this returns 4,327 rows. the old one below returned 3,127 rows
    # TODO: figure out why and if all_csets query in ddl.sql needs to be fixed
    return sql_query(
        con, f""" 
        SELECT codeset_id,
              concept_set_version_title,
              concepts
        FROM {SCHEMA}.all_csets""")
    # smaller = DS2.all_csets[['codeset_id', 'concept_set_version_title', 'concepts']]
    # return smaller.to_dict(orient='records')


# Routes ---------------------------------------------------------------------------------------------------------------
@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list


@APP.get("/get-all-csets")
def _get_all_csets() -> Union[Dict, List]:
    """Route for: get_all_csets()"""
    return get_all_csets()


# TODO: the following is just based on concept_relationship
#       should also check whether relationships exis/{CONFIG["db"]}?charset=utf8mb4't in concept_ancestor
#       that aren't captured here
# TODO: Add concepts outside the list of codeset_ids?
#       Or just make new issue for starting from one cset or concept
#       and fanning out to other csets from there?
@APP.get("/selected-csets")
def _get_csets(codeset_id: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: get_csets()"""
    requested_codeset_ids = parse_codeset_ids(codeset_id)
    return get_csets(requested_codeset_ids)


@APP.get("/related-csets")
def _get_related_csets(codeset_id: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: get_related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return get_related_csets(codeset_ids)


@APP.get("/cset-members-items")
def _cset_members_items(codeset_id: Union[str, None] = Query(default=''), ) -> List[LegacyRow]:
    """Route for: cset_memberss_items()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return get_cset_members_items(codeset_ids)


@APP.get("/hierarchy")
def _hierarchy(codeset_id: Union[str, None] = Query(default=''), ) -> Dict:
    """Route for: hierarchy()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return hierarchy(codeset_ids=codeset_ids)


# TODO: get back to how we had it before RDBMS refactor
@APP.get("/cr-hierarchy")
def cr_hierarchy(rec_format: str = 'default', codeset_id: Union[str, None] = Query(default=''), ) -> Dict:

    # TODO: TEMP FOR TESTING. #191 isn't a problem with the old json data
    # fp = open(r'./backend/old_cr-hierarchy_samples/cr-hierarchy - example1 - before refactor.json')
    # return json.load(fp)

    """Get concept relationship hierarchy

    Example:
    http://127.0.0.1:8000/cr-hierarchy?format=flat&codeset_id=400614256|87065556
    """
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    cset_member_ids: List[int] = get_concept_set_member_ids(codeset_ids, column='concept_id')
    cset_members_items = get_cset_members_items(codeset_ids)

    concept_ids = list(set([i['concept_id'] for i in cset_members_items]))

    items = [mi for mi in cset_members_items if mi['item']]
    item_concept_ids = list(set([i['concept_id'] for i in items]))

    h = hierarchy(root_cids=item_concept_ids, cids=concept_ids)
    # nh = new_hierarchy(root_cids=item_concept_ids, cids=concept_ids)

    related_csets = get_related_csets(codeset_ids=codeset_ids, selected_concept_ids=cset_member_ids)
    selected_csets = [cset for cset in related_csets if cset['selected']]
    researcher_ids = get_all_researcher_ids(related_csets)
    researchers = get_researchers(researcher_ids)

    result = {
        # # todo: Check related_csets() to see its todo's
        'related_csets': related_csets,
        # # todo: Check get_csets() to see its todo's
        'selected_csets': selected_csets,
        'researchers': researchers,
        'cset_members_items': cset_members_items,
        'hierarchy': hierarchy(selected_concept_ids=concept_ids),
        # todo: concepts
        'concepts': [],
        # todo: frontend not making use of data_counts yet but will need
        'data_counts': [],
    }

    # TODO: Fix: concepts missing from hierarchy that shouldn't be:
    h = result['hierarchy']
    hh = json.dumps(h)
    import re
    hierarchy_concept_ids = [int(x) for x in re.findall(r'\d+', hh)]
    # diff for: http://127.0.0.1:8000/cr-hierarchy?rec_format=flat&codeset_id=400614256|87065556
    #  {4218499, 4198296, 4215961, 4255399, 4255400, 4255401, 4147509, 252341, 36685758, 4247107, 4252356, 42536648, 4212441, 761062, 259055, 4235260}
    diff = set(cset_member_ids).difference(hierarchy_concept_ids)

    # TODO: siggie was working on something here
    result['concepts'] = get_concepts(hierarchy_concept_ids)

    # o = json.load(fp)['hierarchy']
    # n = result['hierarchy']
    # print(f"o.keys() == n.keys(): {set(o.keys()) == set(n.keys())}")
    # for k,v in o.items():
    #     if not v == n[k]:
    #         print(k, o[k], n[k])

    return result


# @APP.get("/cset-download")  # maybe junk, or maybe start of a refactor of above
# def cset_download(codeset_id: int) -> Dict:
#     """Download concept set"""
#     dsi = data_stuff_for_codeset_ids([codeset_id])
#
#     concepts = DS2.concept[DS2.concept.concept_id.isin(set(dsi.cset_members_items.concept_id))]
#     cset = DS2.all_csets[DS2.all_csets.codeset_id == codeset_id].to_dict(orient='records')[0]
#     cset['concept_count'] = cset['concepts']
#     cset['concepts'] = concepts.to_dict(orient='records')
#     return cset


# todo: Some redundancy. (i) should only need concept_set_name once
# TODO: @Siggie: Do we want to add: annotation, intended_research_project, and on_behalf_of?
#  - These are params in upload_new_cset_version_with_concepts()  - Joe 2022/12/05
class UploadNewCsetVersionWithConcepts(BaseModel):
    """Schema for route: /upload-new-cset-version-with-concepts

    Upload a concept set version along with its concepts.

    This schema is for POSTing to a FastAPI route.

    Schema:
    :param version_with_concepts (Dict): Has the following schema: {
        'omop_concepts': [
          {
            'concept_id' (int) (required):
            'includeDescendants' (bool) (required):
            'isExcluded' (bool) (required):
            'includeMapped' (bool) (required):
            'annotation' (str) (optional):
          }
        ],
        'provenance' (str) (required):
        'concept_set_name' (str) (required):
        'annotation' (str) (optional): Default:`'Curated value set: ' + version['concept_set_name']`
        'limitations' (str) (required):
        'intention' (str) (required):
        'intended_research_project' (str) (optional): Default:`ENCLAVE_PROJECT_NAME`
        'codeset_id' (int) (required): Default:Will ge generated if not passed.
    }

    # TODO: verify that this example is correct
    Example:
    {
        "omop_concepts": [
            {
              "concept_id": 45259000,
              "includeDescendants": true,
              "isExcluded": false,
              "includeMapped": true,
              "annotation": "This is my concept annotation."
            }
        ],
        "provenance": "Created through TermHub.",
        "concept_set_name": "My test concept set",
        "limitations": "",
        "intention": ""
    }
    """
    omop_concepts: List[Dict]
    provenance: str
    concept_set_name: str
    limitations: str
    intention: str


# todo #123: add baseVersion: the version that the user starts off from in order to create their own new concept set
#  ...version. I need to add the ability to get arbitrary args (*args) including baseVersion, here in these routes and
#  ...in the other functions.
@APP.post("/upload-new-cset-version-with-concepts")
def route_upload_new_cset_version_with_concepts(d: UploadNewCsetVersionWithConcepts) -> Dict:
    """Upload new version of existing container, with concepets"""
    # TODO: Persist: see route_upload_new_container_with_concepts() for more info
    # result = csets_update(dataset_path='', row_index_data_map={})
    response = upload_new_cset_version_with_concepts(**d.__dict__)

    return {}  # todo: return. should include: assigned codeset_id's


# todo: Some redundancy. (i) should only need concept_set_name once
class UploadNewContainerWithConcepts(BaseModel):
    """Schema for route: /upload-new-container-with-concepts

    Upload a concept set container, along with versions version which include concepts.

    This schema is for POSTing to a FastAPI route.

    Schema:
    Should be JSON with top-level keys: container, versions_with_concepts

    :param container (Dict): Has the following keys:
        concept_set_name (str) (required):
        intention (str) (required):
        research_project (str) (required): Default:`ENCLAVE_PROJECT_NAME`
        assigned_sme (str) (optional): Default:`PALANTIR_ENCLAVE_USER_ID_1`
        assigned_informatician (str) (optional): Default:`PALANTIR_ENCLAVE_USER_ID_1`

    :param versions_with_concepts (List[Dict]): Has the following schema: [
      {
        'omop_concepts': [
          {
            'concept_id' (int) (required):
            'includeDescendants' (bool) (required):
            'isExcluded' (bool) (required):
            'includeMapped' (bool) (required):
            'annotation' (str) (optional):
          }
        ],
        'provenance' (str) (required):
        'concept_set_name' (str) (required):
        'annotation' (str) (optional): Default:`'Curated value set: ' + version['concept_set_name']`
        'limitations' (str) (required):
        'intention' (str) (required):
        'intended_research_project' (str) (optional): Default:`ENCLAVE_PROJECT_NAME`
        'codeset_id' (int) (required): Will be generated if not passed.
      }
    ]

    Example:
    {
      "container": {
        "concept_set_name": "My test concept set",
        "intention": "",
        "research_project": "",
        "assigned_sme": "",
        "assigned_informatician": ""
      },
      "versions_with_concepts": [{
        "omop_concepts": [
            {
              "concept_id": 45259000,
              "includeDescendants": true,
              "isExcluded": false,
              "includeMapped": true,
              "annotation": "This is my concept annotation."
            }
        ],
        "provenance": "Created through TermHub.",
        "concept_set_name": "My test concept set",
        "limitations": "",
        "intention": ""
      }]
    }
    """
    container: Dict
    versions_with_concepts: List[Dict]


# todo: see todo '#123'
@APP.post("/upload-new-container-with-concepts")
def route_upload_new_container_with_concepts(d: UploadNewContainerWithConcepts) -> Dict:
    """Upload new container with concepts"""
    # TODO: Persist
    #  - call the function i defined for updating local git stuff. persist these changes and patch etc
    #     dataset_path: File path. Relative to `/termhub-csets/datasets/`
    #     row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are
    #     the name of the fields to be updated, and values contain the values to update in that particular cell."""
    #  - csets_update() doesn't meet exact needs. not actually updating to an existing index. adding a new row.
    #    - soution: can set index to -1, perhaps, to indicate that it is a new row
    #    - edge case: do i need to worry about multiple drafts at this point? delete if one exists? keep multiple? or at
    #    upload time should we update latest and delete excess drafts if exist?
    #  - git/patch changes (do this inside csets_update()):
    #  https://github.com/jhu-bids/TermHub/issues/165#issuecomment-1276557733
    # result = csets_update(dataset_path='', row_index_data_map={})

    response = upload_new_container_with_concepts(
        container=d.container,
        versions_with_concepts=d.versions_with_concepts)

    return {}  # todo: return. should include: assigned codeset_id's


class UploadCsvVersionWithConcepts(BaseModel):
    csv: str


@APP.post("/upload-csv-new-cset-version-with-concepts")
def route_csv_upload_new_cset_version_with_concepts(data: UploadCsvVersionWithConcepts) -> Dict:
    """Upload new version of existing container, with concepets"""
    # noinspection PyTypeChecker
    df = pd.read_csv(StringIO(data.dict()['csv'])).fillna('')
    response: Dict = upload_new_cset_version_with_concepts_from_csv(df=df)
    # print('CSV upload result: ')
    # can't print it, it's all response objects
    # print(json.dumps(response, indent=2))

    # return response # seems to be causing error
    return {"status": "success, I think"}


@APP.post("/upload-csv-new-container-with-concepts")
def route_csv_upload_new_container_with_concepts(data: UploadCsvVersionWithConcepts) -> Dict:
    """Upload new container with concepts"""
    # noinspection PyTypeChecker
    df = pd.read_csv(StringIO(data.dict()['csv'])).fillna('')
    response: Dict = upload_new_cset_container_with_concepts_from_csv(df=df)
    # print('CSV upload result: ')
    # print(json.dumps(response, indent=2))
    return response


# TODO: (i) move most of this functionality out of route into separate function (potentially keeping this route which
#  simply calls that function as well), (ii) can then connect that function as step in the routes that coordinate
#  enclave uploads
# TODO: git/patch changes: https://github.com/jhu-bids/TermHub/issues/165#issuecomment-1276557733
def csets_git_update(dataset_path: str, row_index_data_map: Dict[int, Dict[str, Any]]) -> Dict:
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
  path = os.path.join(path_root, dataset_path)
  # noinspection PyBroadException
  try:
    df = pd.read_csv(path, dtype={'id': np.int32, 'last_name': str, 'first_name': str}).fillna('')
    for index, field_values in row_index_data_map.items():
      for field, value in field_values.items():
        df.at[index, field] = value
    df.to_csv(path, index=False)
  except BaseException as err:
    result = 'failure'
    details = str(err)

  # Push commit
  # todo?: Correct git status after change should show something like this near end: `modified: FILENAME`
  relative_path = os.path.join('datasets', dataset_path)
  # todo: Want to see result as string? only getting int: 1 / 0
  #  ...answer: it's being printed to stderr and stdout. I remember there's some way to pipe and capture if needed
  # TODO: What if the update resulted in no changes? e.g. changed values were same?
  git_add_result = sp_call(f'git add {relative_path}'.split(), cwd=cset_dir)
  if git_add_result != 0:
    result = 'failure'
    details = f'Error: Git add: {dataset_path}'
  git_commit_result = sp_call(['git', 'commit', '-m', f'Updated by server: {relative_path}'], cwd=cset_dir)
  if git_commit_result != 0:
    result = 'failure'
    details = f'Error: Git commit: {dataset_path}'
  git_push_result = sp_call('git push origin HEAD:main'.split(), cwd=cset_dir)
  if git_push_result != 0:
    result = 'failure'
    details = f'Error: Git push: {dataset_path}'

  return {'result': result, 'details': details}


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsGitUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}


# TODO: Maybe change to `id` instead of row index
@APP.put("/datasets/csets")
def put_csets_update(d: CsetsGitUpdate = None) -> Dict:
    """HTTP PUT wrapper for csets_update()"""
    return csets_git_update(d.dataset_path, d.row_index_data_map)


@APP.put("/datasets/vocab")
def vocab_update():
    """Update vocab dataset"""
    pass


if __name__ == '__main__':
    run()
