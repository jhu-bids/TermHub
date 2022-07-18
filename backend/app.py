"""TermHub backend"""
from typing import Union

from fastapi import FastAPI

from enclave_wrangler import config


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World2"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


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
  response = requests.get(url, headers=headers)
  response_json = response.json()
  return response_json['data']


@app.route('/browse-onto')
def browse_onto():
  # object_types = browse_onto_data()
  # return render_template('pages/browse_onto.html', object_types=object_types)
  pass


