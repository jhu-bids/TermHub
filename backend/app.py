"""TermHub backend"""
from typing import Dict, List

import requests
from fastapi import FastAPI

from enclave_wrangler.config import config


app = FastAPI()


@app.get("/")
def read_root():
    # return {"Hello": "World"}
    return ontocall('objectTypes')


def ontocall(path) -> [{}]:
  """API documentation at
  https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
  https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
  """
  headers = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    # 'content-type': 'application/json'
  }
  ontologyRid = config['ONTOLOGY_RID']
  api_path = f'/api/v1/ontologies/{ontologyRid}/{path}'
  url = f'https://{config["HOSTNAME"]}{api_path}'
  print(f'ontocall: {api_path}\n{url}')

  response: List[Dict] = requests.get(url, headers=headers).json()
  response = response['data']
  if path == 'objectTypes':
    apiNames = sorted([
        t['apiName'] for t in response if t['api    Name'].startswith('OMOP')])
    return apiNames

  return {'unrecognized path': path}


@app.route('/browse-onto')
def browse_onto():
  # object_types = browse_onto_data()
  # return render_template('pages/browse_onto.html', object_types=object_types)
  pass


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
