"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Union
from functools import cache

import uvicorn
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from sqlalchemy.engine import LegacyRow, RowMapping

from backend.db.queries import get_all_parent_child_subsumes_tuples
from backend.utils import hierarchify_list_of_parent_kids
from enclave_wrangler.dataset_upload import upload_new_container_with_concepts, upload_new_cset_version_with_concepts
from enclave_wrangler.utils import make_objects_request

from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col

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
    'all_parent_child_subsumes_tuples': get_all_parent_child_subsumes_tuples(CON)
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
#   ['precision', 'status_container', 'concept_set_id', 'rid', 'selected', 'created_at_container', 'created_at_version', 'intention_container', 'researchers', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `get_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention', 'container_status', 'container_created_by']
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
    rows2 = [dict(x) for x in rows]
    rows3 = [populate_researchers(x) for x in rows2]
    return rows3


def get_concepts(concept_ids: List[int], con=CON) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    rows: List[LegacyRow] = sql_query(
        con, """
          SELECT *
          FROM concepts_with_counts
          WHERE concept_id = ANY(:concept_ids);""",
        {'concept_ids': concept_ids})
    return rows


def populate_researchers(codeset_row: Dict) -> Dict:
    """Takes a codeset row (dictionary) and returns a dictionary with researcher info"""
    researcher_cols = ['container_created_by', 'codeset_created_by', 'assigned_sme', 'reviewed_by', 'n3c_reviewer',
                       'assigned_informatician']
    researcher_ids = set()
    row = codeset_row
    for _id in [row[col] for col in researcher_cols if col in row and row[col]]:
        researcher_ids.add(_id)
    row['researchers'] = [get_researcher(_id, fields=['name']) for _id in researcher_ids]
    return row


def get_researcher(_id: int, fields: List[str] = None) -> List[Dict]:
    """Get researcher info"""
    query = f"""
        SELECT {', '.join([f'"{x}"' for x in fields])}
        FROM researcher
        WHERE "multipassId" = :id
    """
    res: List[RowMapping] = sql_query(CON, query, {'id': _id}, return_with_keys=True)
    res2: List[Dict] = [{**{'id': _id}, **{k: v for k, v in dict(x).items()}} for x in res]

    return res2


# TODO
#  i. Keys in our old `related_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'selected', 'created_at_container', 'created_at_version', 'intention_container', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `related_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention', 'container_status', 'container_created_by']
#  see fixes above. i think everything here is fixed now
def related_csets(codeset_ids: List[int] = None, selected_concept_ids: List[int] = None, con=CON) -> List[Dict]:
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
    for cset in related_csets:
        cids = get_concept_set_member_ids([cset['codeset_id']], column='concept_id')
        intersecting_concepts = set(cids).intersection(selected_cids)
        cset['intersecting_concepts'] = len(intersecting_concepts)
        cset['recall'] = cset['intersecting_concepts'] / selected_cid_cnt
        cset['precision'] = cset['intersecting_concepts'] / len(cids)
        cset['selected'] = cset['codeset_id'] in codeset_ids
    return related_csets


def cset_members_items(codeset_ids: List[int] = None, con=CON) -> List[LegacyRow]:
    return sql_query(
        con, f""" 
        SELECT *
        FROM cset_members_items
        WHERE codeset_id = ANY(:codeset_ids)
        """,
        {'codeset_ids': codeset_ids})


def hierarchy(codeset_ids: List[int] = None, selected_concept_ids: List[int] = None, con=CON) -> Dict:
    """Get hierarchy of concepts in selected concept sets"""
    # it's ok to get an empty list
    # if not codeset_ids and not selected_concept_ids:
    #     raise ValueError('Must provide either codeset_ids or selected_concept_ids')
    if not selected_concept_ids:
        selected_concept_ids = get_concept_set_member_ids(codeset_ids, column='concept_id')

    # sql speed: 36-48sec concept_relationship (n=16,971,521). 1.8sec concept_relationship_subsumes_only (n=875,090)
    t0 = datetime.now()
    all_parent_child_list = CACHE['all_parent_child_subsumes_tuples']
    t1 = datetime.now()
    print(f"Time to get concept_relationship_subsumes_only: {t1 - t0}")

    selected_roots: List[int] = top_level_cids(selected_concept_ids)
    d = hierarchify_list_of_parent_kids(all_parent_child_list, selected_roots)

    # todo: this may not be the most efficient way to do this
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
        45936903, 40545669, 45921434, 45917166, 4110177, 3141624, 40316548, 44808238, 4169883, 45945309, 3124228, 40395876, 3151089, 40316547, 40563017, 44793048,
        ...
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


def top_level_cids(concept_ids: List[int], con=CON) -> List[int]:
    """Filter to concept ids with no parents"""
    top_level_cids = sql_query_single_col(
        con, f""" 
        SELECT DISTINCT concept_id_1
        FROM concept_relationship cr
        WHERE cr.concept_id_1 = ANY(:concept_ids)
          AND cr.relationship_id = 'Subsumes'
          AND NOT EXISTS (
            SELECT *
            FROM concept_relationship
            WHERE concept_id_2 = cr.concept_id_1
          )
        """,
        {'concept_ids': concept_ids})
    return top_level_cids


def top_level_cids(concept_ids: List[int], con=CON) -> List[int]:
    """Filter to concept ids with no parents"""
    top_level_cids = sql_query_single_col(
        con, f""" 
        WITH cids AS (
            SELECT unnest(ARRAY[:concept_ids]) AS concept_id
        ) -- , standalone AS (  -- these are cids with no parents or children, will be included as top level
            SELECT DISTINCT concept_id
            FROM cids
            WHERE NOT EXISTS (
                SELECT *
                FROM concept_relationship cr
                WHERE cr.relationship_id = 'Subsumes'
                  AND cr.concept_id_2 = cids.concept_id
                  AND cr.concept_id_1 IN (SELECT concept_id from cids)
                   --OR  cr.concept_id_2 = cids.concept_id)
            )
        """,
        {'concept_ids': concept_ids})
        # ), no_parents AS (  -- these have no parents (in cids), so are top level
        #     SELECT cids.concept_id
        #     FROM cids
        #     WHERE NOT EXISTS (
        #         SELECT *
        #         FROM concept_relationship cr
        #         WHERE cr.relationship_id = 'Subsumes'
        #           AND (cr.concept_id_1 = cids.concept_id
        #            OR  cr.concept_id_2 = cids.concept_id)
        #     )
        #     FROM concept_relationship cr
        #     WHERE cr.concept_id_1 = ANY(:concept_ids)
        #       AND cr.relationship_id = 'Subsumes'
        #       AND NOT EXISTS (
        #         SELECT *
        #         FROM concept_relationship
        #         WHERE concept_id_2 = cr.concept_id_1
        #       )
        # )
    return top_level_cids


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
def _related_csets(codeset_id: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return related_csets(codeset_ids)


@APP.get("/cset-members-items")
def _cset_members_items(codeset_id: Union[str, None] = Query(default=''), ) -> List[LegacyRow]:
    """Route for: related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return cset_members_items(codeset_ids)


@APP.get("/hierarchy")
def _hierarchy(codeset_id: Union[str, None] = Query(default=''), ) -> Dict:
    """Route for: related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return hierarchy(codeset_ids=codeset_ids)


# TODO: get back to how we had it before RDBMS refactor
@APP.get("/cr-hierarchy")
def cr_hierarchy(rec_format: str = 'default', codeset_id: Union[str, None] = Query(default=''), ) -> Dict:

    # TODO: TEMP FOR TESTING. #191 isn't a problem with the old json data
    # fp = open('./backend/old_cr-hierarchy_samples/cr-hierarchy-example1.json')
    # return json.load(fp)

    """Get concept relationship hierarchy

    Example:
    http://127.0.0.1:8000/cr-hierarchy?format=flat&codeset_id=400614256|87065556
    """
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    cset_member_ids: List[int] = get_concept_set_member_ids(codeset_ids, column='concept_id')

    # Old LFS way, for reference
    # dsi = cset_members(requested_codeset_ids)
    # result = {
    #           # 'all_csets': dsi.all_csets.to_dict(orient='records'),
    #           'related_csets': dsi.related_csets.to_dict(orient='records'),
    #           'selected_csets': dsi.selected_csets.to_dict(orient='records'),
    #           # 'concept_set_members_i': dsi.concept_set_members_i.to_dict(orient='records'),
    #           # 'concept_set_version_item_i': dsi.concept_set_version_item_i.to_dict(orient='records'),
    #           'cset_members_items': dsi.cset_members_items.to_dict(orient='records'),
    #           'hierarchy': dsi.hierarchy,
    #           'concepts': dsi.concepts.to_dict(orient='records'),
    #           'data_counts': log_counts(),
    # }

    # TODO: uncomment
    result = {
        # # todo: Check related_csets() to see its todo's
        'related_csets': related_csets(codeset_ids=codeset_ids, selected_concept_ids=cset_member_ids),
        # # todo: Check get_csets() to see its todo's
        'selected_csets': get_csets(codeset_ids),
        'cset_members_items': cset_members_items(codeset_ids),
        'hierarchy': hierarchy(selected_concept_ids=cset_member_ids),
        # todo: concepts
        'concepts': [],
        # todo: frontend not making use of data_counts yet but will need
        'data_counts': [],
    }
    result['concepts'] = get_concepts([i.concept_id for i in result['cset_members_items']])

    return result


@APP.get("/cset-download")  # maybe junk, or maybe start of a refactor of above
def cset_download(codeset_id: int) -> Dict:
    """Download concept set"""
    dsi = data_stuff_for_codeset_ids([codeset_id])

    concepts = DS2.concept[DS2.concept.concept_id.isin(set(dsi.cset_members_items.concept_id))]
    cset = DS2.all_csets[DS2.all_csets.codeset_id == codeset_id].to_dict(orient='records')[0]
    cset['concept_count'] = cset['concepts']
    cset['concepts'] = concepts.to_dict(orient='records')
    return cset


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


# TODO #123: add baseVersion: the version that the user starts off from in order to create their own new concept set
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


# TODO: see todo '#123'
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
