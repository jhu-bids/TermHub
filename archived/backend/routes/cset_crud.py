"""Routes for concept set CRUD operations

Resources:
  - https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List
from subprocess import call as sp_call

import numpy as np
import pandas as pd
from fastapi import APIRouter
# from fastapi import APIRouter, Depends, HTTPException
# from ..dependencies import get_token_header  # from FastAPI example
from pydantic import BaseModel

from backend.utils import return_err_with_trace
from enclave_wrangler.dataset_upload import upload_new_container_with_concepts, \
    upload_new_cset_container_with_concepts_from_csv, upload_new_cset_version_with_concepts, \
    upload_new_cset_version_with_concepts_from_csv
from enclave_wrangler.utils import EnclaveWranglerErr


PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
router = APIRouter(
    # prefix="/cset-crud",
    # tags=["cset-crud"],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)


# todo: Some redundancy. (i) should only need concept_set_name once
class UploadJsonNewContainerWithConcepts(BaseModel):
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


# todo: Some redundancy. (i) should only need concept_set_name once
# TODO: @Siggie: Do we want to add: annotation, intended_research_project, and on_behalf_of?
#  - These are params in upload_new_cset_version_with_concepts()  - Joe 2022/12/05
class UploadJsonNewCsetVersionWithConcepts(BaseModel):
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


class UploadCsvVersionWithConcepts(BaseModel):
    """Base model for route: /upload-csv-new-cset-version-with-concepts"""
    csv: str


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsGitUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}


@router.post("/create-new-draft-omop-concept-set-version")
def route_create_new_draft_omop_concept_set_version(d: UploadJsonNewCsetVersionWithConcepts) -> Dict:
    """Upload new version of existing container, with concepets"""
    api_name = 'create-new-draft-omop-concept-set-version'
    # TODO: Persist: see route_upload_new_container_with_concepts() for more info
    # result = csets_update(dataset_path='', row_index_data_map={})
    try:
        response = upload_new_cset_version_with_concepts(**d.__dict__)
    except EnclaveWranglerErr as e:
        print(e, file=sys.stderr)
        return {'error': str(e)}

    return response  # todo: return. should include: assigned codeset_id's


# todo #123: add baseVersion: the version that the user starts off from in order to create their own new concept set
#  ...version. I need to add the ability to get arbitrary args (*args) including baseVersion, here in these routes and
#  ...in the other functions.
@router.post("/upload-json-new-cset-version-with-concepts")
def route_upload_json_new_cset_version_with_concepts(d: UploadJsonNewCsetVersionWithConcepts) -> Dict:
    """Upload new version of existing container, with concepets"""
    # TODO: Persist: see route_upload_new_container_with_concepts() for more info
    # result = csets_update(dataset_path='', row_index_data_map={})
    try:
        response = upload_new_cset_version_with_concepts(**d.__dict__)
    except EnclaveWranglerErr as e:
        print(e, file=sys.stderr)
        return {'error': str(e)}

    return response  # todo: return. should include: assigned codeset_id's


# todo: see todo '#123'
@router.post("/upload-json-new-container-with-concepts")
def route_json_upload_new_container_with_concepts(d: UploadJsonNewContainerWithConcepts) -> Dict:
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
        concept_set_name=d.container['concept_set_name'],
        intention=d.container['intention'],
        research_project=d.container['research_project'],
        assigned_sme=d.container['assigned_sme'],
        assigned_informatician=d.container['assigned_informatician'],
        versions_with_concepts=d.versions_with_concepts)

    return response  # todo: return. should include: assigned codeset_id's


@router.post("/upload-csv-new-cset-version-with-concepts")
@return_err_with_trace
def route_csv_upload_new_cset_version_with_concepts(data: UploadCsvVersionWithConcepts) -> Dict:
    """Upload new version of existing container, with concepets"""
    result = {}
    try:
        # noinspection PyTypeChecker
        df = pd.read_csv(StringIO(data.dict()['csv'])).fillna('')
        response: Dict = upload_new_cset_version_with_concepts_from_csv(df=df, validate_first=False)
    except Exception as e:  # todo: this will be refactored so that every request returns err
        try:
            # noinspection PyTypeChecker
            df = pd.read_csv(StringIO(data.dict()['csv'])).fillna('')
            response: Dict = upload_new_cset_version_with_concepts_from_csv(df=df, validate_first=True)
        except Exception as e:
            result['status'] = 'error'
            result['errors'] = str(e)
            return result

    for cset_name, data in response.items():
        results = data['responses'] if 'responses' in data else data
        errors = {}
        for k, v in results.items():
            if isinstance(v, list):
                for i, vv in enumerate(v):
                    if vv.status_code >= 400:
                        errors[f'{k}[{i}]'] = vv.text
            elif v.status_code >= 400:
                errors[k] = v.text
        result[cset_name] = {
            'versionId': data['versionId'],
        }
        if errors:
            result[cset_name]['errors'] = errors
            result[cset_name]['status'] = 'error'
        else:
            result[cset_name]['status'] = 'success'

    result['status'] = 'error' if any([v['status'] == 'error' for v in result.values()]) else 'success'
    return result


@router.post("/upload-csv-new-container-with-concepts")
def route_csv_upload_new_container_with_concepts(data: UploadCsvVersionWithConcepts) -> Dict:
    """Upload new container with concepts"""
    # noinspection PyTypeChecker
    df = pd.read_csv(StringIO(data.dict()['csv'])).fillna('')
    response: Dict = upload_new_cset_container_with_concepts_from_csv(df=df)
    return response
