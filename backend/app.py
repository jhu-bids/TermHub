"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
from typing import Any, Dict, List, Union, Set
from functools import cache

import uvicorn
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from enclave_wrangler.dataset_upload import upload_new_container_with_concepts, upload_new_cset_version_with_concepts
from enclave_wrangler.datasets import run_favorites as update_termhub_csets
from enclave_wrangler.new_enclave_api import make_read_request

from backend.utils import cnt # , pdump
from backend.db.utils import run_sql, get_db_connection, sql_query, get_concept_set_members

CON = get_db_connection()  # using a global connection object is probably a terrible idea, but
                              # shouldn't matter much until there are multiple users on the same server
@cache
def parse_codeset_ids(qstring):
    if not qstring:
        return []
    requested_codeset_ids = qstring.split('|')
    requested_codeset_ids = [int(x) for x in requested_codeset_ids]
    return requested_codeset_ids

# Routes ---------------------------------------------------------------------------------------------------------------
APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)


@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list


@APP.get("/get-all-csets")
def get_all_csets() -> Union[Dict, List]:
  # this returns 4,327 rows. the old one below returned 3,127 rows
  # TODO: figure out why and if all_csets query in ddl.sql needs to be fixed

  return sql_query(
    CON, """ 
    SELECT codeset_id,
          concept_set_version_title,
          concepts
    FROM all_csets""")
    # smaller = DS2.all_csets[['codeset_id', 'concept_set_version_title', 'concepts']]
    # return smaller.to_dict(orient='records')


# TODO: the following is just based on concept_relationship
#       should also check whether relationships exis/{CONFIG["db"]}?charset=utf8mb4't in concept_ancestor
#       that aren't captured here
# TODO: Add concepts outside the list of codeset_ids?
#       Or just make new issue for starting from one cset or concept
#       and fanning out to other csets from there?
# Example: http://127.0.0.1:8000/cr-hierarchy?codeset_id=818292046&codeset_id=484619125&codeset_id=400614256
@APP.get("/selected-csets")
def selected_csets(codeset_id: Union[str, None] = Query(default=''), ) -> Dict:
  requested_codeset_ids = parse_codeset_ids(codeset_id)
  return sql_query(CON, """
      SELECT *
      FROM all_csets
      WHERE codeset_id = ANY(:codeset_ids);""",
                   {'codeset_ids': requested_codeset_ids})
  # {'codeset_ids': ','.join([str(id) for id in requested_codeset_ids])})


@APP.get("/related-csets")
def related_csets(codeset_id: Union[str, None] = Query(default=''), ) -> Dict:
  requested_codeset_ids = parse_codeset_ids(codeset_id)
  return get_concept_set_members(CON, requested_codeset_ids, column='concept_id')


@APP.get("/cr-hierarchy")  # maybe junk, or maybe start of a refactor of above
def cr_hierarchy( rec_format: str='default', codeset_id: Union[str, None] = Query(default=''), ) -> Dict:

    # print(ds) uncomment just to put ds in scope for looking at in debugger
    requested_codeset_ids = parse_codeset_ids(codeset_id)
    # A namespace (like `ds`) specifically for these codeset IDs.
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)

    result = {
              # 'all_csets': dsi.all_csets.to_dict(orient='records'),
              'related_csets': dsi.related_csets.to_dict(orient='records'),
              'selected_csets': dsi.selected_csets.to_dict(orient='records'),
              # 'concept_set_members_i': dsi.concept_set_members_i.to_dict(orient='records'),
              # 'concept_set_version_item_i': dsi.concept_set_version_item_i.to_dict(orient='records'),
              'cset_members_items': dsi.cset_members_items.to_dict(orient='records'),
              'hierarchy': dsi.hierarchy,
              'concepts': dsi.concepts.to_dict(orient='records'),
              'data_counts': log_counts(),
    }
    return result


@APP.get("/cset-download")  # maybe junk, or maybe start of a refactor of above
def cset_download(codeset_id: int) -> Dict:
  dsi = data_stuff_for_codeset_ids([codeset_id])

  concepts = DS2.concept[DS2.concept.concept_id.isin(set(dsi.cset_members_items.concept_id))]
  cset = DS2.all_csets[DS2.all_csets.codeset_id == codeset_id].to_dict(orient='records')[0]
  cset['concept_count'] = cset['concepts']
  cset['concepts'] = concepts.to_dict(orient='records')
  return cset


@cache
def get_container(concept_set_name):
    """This is for getting the RID of a dataset. This is available via the ontology API, not the dataset API.
    TODO: This needs caching, but the @cache decorator is not working."""
    return make_read_request(f'objects/OMOPConceptSetContainer/{urllib.parse.quote(concept_set_name)}')

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
    #     row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
    #       name of the fields to be updated, and values contain the values to update in that particular cell."""
    #  - csets_update() doesn't meet exact needs. not actually updating to an existing index. adding a new row.
    #    - soution: can set index to -1, perhaps, to indicate that it is a new row
    #    - edge case: do i need to worry about multiple drafts at this point? delete if one exists? keep multiple? or at upload time
    #    ...should we update latest and delete excess drafts if exist?
    #  - git/patch changes (do this inside csets_update()): https://github.com/jhu-bids/TermHub/issues/165#issuecomment-1276557733
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


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
