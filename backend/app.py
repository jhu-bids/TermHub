"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
- jq docs: https://stedolan.github.io/jq/manual/
- jq python api docs: https://github.com/mwilliamson/jq.py
"""
import json
import os.path
from pathlib import Path
from subprocess import PIPE, Popen, call as sp_call
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from enclave_wrangler.config import config


PROJECT_DIR = Path(os.path.dirname(__file__)).parent
CSETS_JSON_PATH = f'{PROJECT_DIR}/termhub-csets/temp/objects/OMOPConceptSet/latest.json'
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)


# Utils
def jq_wrapper(query: str):
    """Shim around Python->Shell for calling JQ. Useful until/if we change to the JQ Python API."""
    p = Popen(query, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    output, err = p.communicate()
    output = output.decode("utf-8")
    err = err.decode("utf-8")
    return output, err


# Routes
@app.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in app.routes]
    return url_list
    # return {"try": "/ontocall?path=<enclave path after '/api/v1/ontologies/'>",
    #         "example": "/ontocall?path=objects/list-objects/"}
    # return ontocall('objectTypes')


@app.get("/passthru")
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
    print(f'ontocall: {api_path}\n{url}')

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json: Dict = response.json()
        return response_json
    except BaseException as err:
        print(f"Unexpected {type(err)}: {str(err)}")
        return {'ERROR': str(err)}


@app.get("/ontocall")
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
    # if path.startswith('objectTypes/'):
    #     return json
    # return {'valid but unhandled path': path, 'json': json}


@app.put("/datasets/vocab")
def vocab_update():
    """Update vocab dataset"""
    pass


@app.get("linkTypesForObjectTypes")
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


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}


@app.get("/concept-set-names")
@app.get("/datasets/csets/names")
@app.get("/jq-cset-names")
def cset_names() -> Union[Dict, List]:
    """Get concept set names"""
    return csets_read(field_filter=['conceptSetNameOMOP'])


@app.get("/datasets/csets")
def csets_read(field_filter: Union[List[str], None] = Query(default=None)) -> Union[Dict, List]:
    """Get concept sets

    field_filter: If present, the data returned will only contain these fields. Example: Passing `conceptSetNameOMOP` as
    the only field_filter for OMOPConceptSet will return a string list of concept set names.

    Resources: jq docs: https://stedolan.github.io/jq/manual/ , jq python api doc: https://github.com/mwilliamson/jq.py
    """
    if field_filter:
        if len(field_filter) > 1:
            d = {'error': 'Currently only 1 field_filter is allowed.'}
        else:
            # TODO: Need to replace this with Python API. Otherwise, deployment will be harder and must global
            #  installation of JQ.
            query = f"jq '.[] | .{field_filter[0]}' {CSETS_JSON_PATH}"
            output, err = jq_wrapper(query)
            if err:
                return {'error': str('error')}
            d = output.split('\n')
            # x[1:-1]: What gets returned is a \n-delimited string of names, where each name is formatted
            # as '"{NAME}"',so we need to remove the extra set of quotations.
            # TODO: This operation likely needs to be done in a variety of cases, but I don't know JQ well enough to
            #  anticipate all of the situations where this might arise. - joeflack4 2022/08/24
            # todo: Is this List[str] preferable to List[Dict,? e.g. [{'conceptSetNameOMOP': 'HEART FAILURE'}, ...]?
            d = [x[1:-1] for x in d]
            return d
    else:
        with open(CSETS_JSON_PATH, 'r') as f:
            d = json.load(f)
    return d


# TODO: Maybe change to `id` instead of row index
@app.put("/datasets/csets")
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


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
