"""TermHub backend
https://github.com/tiangolo/fastapi"""
from typing import Dict, List

import requests
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from enclave_wrangler.config import config


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)


@app.get("/")
def read_root():
    """Root route"""
    return {"try": "/ontocall?path=<enclave path after '/api/v1/ontologies/'>",
            "example": "/ontocall?path=objects/list-objects/"}
    # return ontocall('objectTypes')

@app.get("linkTypesForObjectTypes")
def linkTypes(path) -> [{}]:
    """
    TODO write this api call?
    TODO        curl below gets json for
    curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" "https://unite.nih.gov/ontology-metadata/api/ontology/linkTypesForObjectTypes" --data '{
        "objectTypeVersions": {
            "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e": "00000001-9834-2acf-8327-ecb491e69b5c"
        }
    }'
    jq '..|objects|.apiName//empty' $@
    """
    pass


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
        response: List[Dict] = requests.get(url, headers=headers)
        response.raise_for_status()
        json = response.json()
        if 'data' in json:
            data = json['data']
        else:
            data = json
        if 'properties' in data:
            data = data['properties'] # e.g., http://127.0.0.1:8000/ontocall?path=objects/OMOPConceptSet/729489911
            data['rid'] = json['rid']
    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")
        return {'ERROR': str(err)}

    return data

    # noinspection PyTypeChecker
    if path == 'objectTypes':
        # data = json['data']
        print(data)
        return data
        api_names = sorted([
            t['apiName'] for t in data if t['apiName'].startswith('OMOP')])
        return api_names
    if path.startswith('objectTypes/'):
        return json
    if path.startswith('objectTypes/'):
        return json

    return {'valid but unhandled path': path, 'json': json}


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
