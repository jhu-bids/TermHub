"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
from typing import Any, Dict, List, Union
from functools import cache

import uvicorn
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from sqlalchemy.engine import LegacyRow

from enclave_wrangler.dataset_upload import upload_new_container_with_concepts, upload_new_cset_version_with_concepts
from enclave_wrangler.utils import make_objects_request

from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col

# CON: using a global connection object is probably a terrible idea, but shouldn't matter much until there are multiple
# users on the same server
CON = get_db_connection()
APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)


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
) -> List[int]:
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
    res = sql_query(con, query, {'codeset_ids': codeset_ids}, debug=False)
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        return [r[0] for r in res]
    return res


# TODO
#  i. Keys in our old `selected_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'rid', 'selected', 'created_at_container', 'created_at_version', 'intention_container', 'researchers', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `selected_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention', 'container_status', 'container_created_by']
#  fixes:
#       probably don't need precision etc.
#       switched _container suffix on duplicate col names to container_ prefix
#       joined OMOPConceptSet in the all_csets ddl to get `rid`
#  still need to fix:
#       researchers
def get_csets(codeset_ids: List[int], con=CON) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    rows: List[LegacyRow] = sql_query(
        con, """
          SELECT *
          FROM all_csets
          WHERE codeset_id = ANY(:codeset_ids);""",
        {'codeset_ids': codeset_ids})
    # {'codeset_ids': ','.join([str(id) for id in requested_codeset_ids])})
    return [dict(x) for x in rows]


# TODO: implement
def get_researcher_info(codeset_id: int):
    researcher_cols = ['created_by_container', 'created_by_version', 'assigned_sme', 'reviewed_by', 'n3c_reviewer',
                       'assigned_informatician']
    researcher_ids = set()
    for i, row in dsi.selected_csets.iterrows():
        for _id in [row[col] for col in researcher_cols if hasattr(row, col) and row[col]]:
            researcher_ids.add(_id)

    get_researcher(researcher_ids)
    # researchers: List[Dict] = DS2.researcher[DS2.researcher['multipassId'].isin(researcher_ids)].to_dict(orient='records')
    # dsi.selected_csets['researchers'] = researchers


def get_researcher(researcher_ids: List[str]):
    pass


# TODO
#  i. Keys in our old `related_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'selected', 'created_at_container', 'created_at_version', 'intention_container', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `related_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention', 'container_status', 'container_created_by']
#  see fixes above. i think everything here is fixed now
def related_csets(codeset_ids: List[int] = None, selected_concept_ids: List[int] = None, con=CON) -> List[Dict]:
    """Get information about concept sets related to those selected by user"""
    if (not codeset_ids and not selected_concept_ids) or (codeset_ids and selected_concept_ids):
        raise RuntimeError('related_csets: Requires 1 of `selected_concept_ids` or `codeset_ids`.')
    elif codeset_ids:
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


def cset_members_items(codeset_ids: List[int] = None, con=CON) -> List[Dict]:
    return sql_query(
        con, f""" 
        SELECT *
        FROM cset_members_items
        WHERE codeset_id = ANY(:codeset_ids)
        """,
        {'codeset_ids': codeset_ids})


def hierarchy(codeset_ids: List[int] = None, con=CON) -> List[Dict]:
    selected_concept_ids = get_concept_set_member_ids(codeset_ids)
    top_level_cids = sql_query_single_col(
        con, f""" 
        SELECT concept_id
        FROM cset_members_items csm
        LEFT JOIN concept_relationship cr ON csm.concept_id = cr.concept_id_2
                                         AND cr.relationship_id = 'Subsumes'
        WHERE codeset_id = ANY(:codeset_ids)
          AND cr.concept_id_2 IS NULL
        """,
        {'codeset_ids': codeset_ids})

    return top_level_cids
    hier = sql_query(
        con, """
        WITH RECURSIVE hier(concept_id_1, concept_id_2, depth) AS (                                                                                                                                                          
            SELECT concept_id_1, concept_id_2, 0 AS depth
            FROM concept_relationship
            WHERE concept_id_1 = ANY(:top_level_cids)
            UNION -- ALL                                                                                                                                                                               
            SELECT cr.concept_id_1, cr.concept_id_2, hier.depth + 1
            FROM concept_relationship cr 
            JOIN hier ON cr.concept_id_1 = hier.concept_id_2
        )                                                                                                                                                                                     
        SELECT * FROM hier
        """,
        {'top_level_cids': top_level_cids})

    junk = """
    -- example used in http://127.0.0.1:8080/backend/old_cr-hierarchy_samples/cr-hierarchy-example1.json 
    -- 411456218|40061425|484619125|419757429
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
            3153572, 45938316, 45913803, 40300133, 3124991, 40545662, 44805920, 45910696, 4141622, 40337129, 40345721, 44807085, 2108536, 40395891, 40300136, 3137830,
            40545249, 3352113, 3124988, 40561687, 45924727, 3150866, 45938784, 3141621, 40316544, 40395881, 40545253, 45906038, 45939036, 3141622, 40395878, 40544275,
            45938447, 3162019, 40395537, 45954259, 3156397, 45920275, 45948999, 3074097, 40337131, 40337132, 3099599, 40297859, 44821987, 46284163, 4112669, 40566165,
            45939199, 4110642, 45935503, 40389375, 3124996, 4144104, 40316543, 40545664, 40546234, 45940320, 40345717, 3137832, 43021747, 45909236, 40297857, 1569488,
            40345758, 45948039, 44804338, 4283362, 40395889, 3201654, 44809514, 3150867, 3099584, 45939829, 40395885, 40566169, 40345719, 4119299, 40395882, 45936352,
            3137829, 40345760, 40545666, 40546155, 3105910, 3150937, 4112831, 44806369, 3137831, 45907808, 3080832, 3150934, 3155659, 45940512, 40545663, 40300138,
            44807940, 40395540, 2101898, 3150869, 3159274, 3124990, 40381380, 3124989, 3079647, 3105911, 4235703, 40395887, 40664872, 45943393, 45908186, 45927141,
            45944861, 3141647, 44793074, 40307557, 40303860, 3064432, 45920173, 3150865, 3150868, 3112998, 3124995, 3151306, 3105913, 40545246, 45949000, 45954260,
            3099585, 3137833, 4119299, 3105910, 3557638, 2617798, 45906019, 45926650, 3067242, 45924581, 3105909, 3124994, 4017187, 3112997, 44788836, 3161077,
            4112670, 4112831, 3080832, 4170623, 3137829, 2617554, 40545251, 40545665, 45917669, 4244061, 4283362, 40345719, 762862, 3150935, 3201654, 45948183,
            3151160, 40307538, 40337152, 3163987, 45939829, 40307535, 45911260, 45945887, 40345717, 45943394, 45955026, 45955255, 40563020, 3124967, 45907865, 45939199,
            40389375, 45940320, 4112669, 45924275, 40664816, 45951072, 45907864, 3124993, 4214588, 3079384, 45939036, 40337130, 3150940, 4057432, 4163244, 3141622,
            40316544, 3141621, 3162019, 3124988, 3125023, 3379022, 45949333, 3161263, 3466410, 40307554, 40395880, 40561687, 40395878, 40547144, 45946099, 40395891,
            3137830, 3099598, 40640771, 3124991, 40307536, 44805004, 45946240, 3150871, 40300134, 3124228, 3153572, 45938316, 45955254, 3467849, 3125021, 44806050,
            37396521, 45936680, 3099587, 40395876, 40436413, 3150936, 45917166, 3124987, 3150938, 3158690, 45913937, 45941262, 40316545, 40337153, 45932474, 3164757,
            3141623, 45909769, 2617553, 3067259, 3105912, 40307556, 40628141, 3124964, 3163091, 4137804, 45909454, 40316546, 3078828, 3141648, 45944525, 40395890, 3066368, 45946655
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
    return hier


def child_cids(concept_id: int, con=CON) -> List[Dict]:
    selected_concept_ids = get_concept_set_member_ids(concept_id)
    top_level_cids = sql_query_single_col(
        con, f""" 
        SELECT DISTINCT concept_id_2
        FROM concept_relationship cr
        WHERE cr.concept_id_1 = ANY(:concept_ids)
          AND cr.relationship_id = 'Subsumes'
        """,
        {'concept_id': concept_id})
    return top_level_cids


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
def _cset_members_items(codeset_id: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return cset_members_items(codeset_ids)


@APP.get("/hierarchy")
def _hierarchy(codeset_id: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_id)
    return hierarchy(codeset_ids)


# TODO: get back to how we had it before RDBMS refactor
@APP.get("/cr-hierarchy")
def cr_hierarchy(rec_format: str = 'default', codeset_id: Union[str, None] = Query(default=''), ) -> Dict:
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

    result = {
        # todo: Check related_csets() to see its todo's
        'related_csets': related_csets(cset_member_ids=cset_member_ids),
        # todo: Check get_csets() to see its todo's
        'selected_csets': get_csets(codeset_ids),
        'cset_members_items': cset_members_items(codeset_ids),
        'hierarchy': [],
        'concepts': [],
        'data_counts': [],
    }
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
