
@app.route('/browse-onto')
def browse_onto():
  object_types = browse_onto_data()
  return render_template('pages/browse_onto.html', object_types=object_types)


def load_concept_sets(by_id: bool = False) -> Dict[str, str]:
  # TODO: maybe move this later
  TERMHUB_DIR = os.path.dirname(os.path.realpath(__file__))
  # DATASETS_DIR = os.path.join(TERMHUB_DIR, '..', 'termhub-csets')
  # concept_set_names_df = pd.read_csv(os.path.join(DATASETS_DIR, 'codesets-junk.csv'), sep='\t')
  # todo : temporarily moved this file
  concept_set_names_df = pd.read_csv(os.path.join(TERMHUB_DIR, 'codesets-junk.csv'), sep='\t')
  concept_sets = {}
  for _index, row in concept_set_names_df.iterrows():
    if by_id:
      concept_sets[str(row['codeset_id'])] = row['concept_set_name']
    else:
      concept_sets[row['concept_set_name']] = row['codeset_id']
  return concept_sets


@app.route('/concept-sets')
def concept_sets():
  concept_sets: Dict = load_concept_sets()
  return render_template('pages/concept_sets.html', concept_sets=concept_sets)


# TODO: AssertionError: View function mapping is overwriting an existing endpoint function: concept_sets
@app.route('/concept-sets/<concept_set_id>')
def concept_set(concept_set_id: str):
  concept_sets: Dict = load_concept_sets(by_id=True)
  concept_set_name: str = concept_sets[concept_set_id]
  return render_template('pages/concept_set.html', concept_set_id=concept_set_id, concept_set_name=concept_set_name)


@app.route('/fhir-terminology')
def fhir_terminology():
  return fhir_terminology_i()


# TODO: standardize this use case. right now this is just an experiment
@app.route('/fhir-terminology/<api_url_id>')
def fhir_terminology_i(api_url_id: str = '1'):
  """FHIR Terminology
  http://20.119.216.32:8080/fhir/"""
  # TODO: for some reason code systems etc aren't fetching from url dynamically
  # TODO: need when select from dropdown, actually follows link. look at url_for from main.html
  # TODO: Show only a subset of the JSON returned
  fhir_api_urls: Dict[int, str] = CONFIG['fhir_api_urls']
  fhir_api_base_url = fhir_api_urls[int(api_url_id)]
  fhir_codesystem_url = fhir_api_base_url + 'CodeSystem'
  fhir_valueset_url = fhir_api_base_url + 'ValueSet'
  fhir_conceptmap_url = fhir_api_base_url + 'ConceptMap'
  code_systems = requests.get(fhir_codesystem_url).json()
  value_sets = requests.get(fhir_valueset_url).json()
  concept_maps = requests.get(fhir_conceptmap_url).json()
  return render_template('pages/fhir_terminology.html',
                         fhir_api_url_selection_id=int(api_url_id),
                         fhir_api_urls=fhir_api_urls,
                         code_systems=code_systems,
                         value_sets=value_sets,
                         concept_maps=concept_maps)


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
  response = requests.get(url, headers=headers,)
  response_json = response.json()
  return response_json['data']


class OntoCall(Resource):
  """Get ontology objects
  - Outdated docs: https://flask-restful.readthedocs.io/en/latest/quickstart.html#argument-parsing
  - If we want to add request validation:
    https://stackoverflow.com/questions/30779584/flask-restful-passing-parameters-to-get-request"""
  def get(self, path):
    # Example response is a list of dictionairies that lok like this:
    # {
    #   "properties": {
    #     "conceptSetId": " Heavy menstrual bleeding",
    #     "assignedInformatician": "4b054b72-ee25-48ca-9183-696cb9bff7ee",
    #     "archived": true,
    #     "stage": "Awaiting Editing",
    #     "alias": "heavy_menstrual_bleeding",
    #     "createdAt": "2021-07-28T19:20:04.268Z",
    #     "createdBy": "976125fc-a13b-4571-a5bd-52c1918ff99b",
    #     "conceptSetName": " Heavy menstrual bleeding",
    #     "status": "Under Construction",
    #     "intention": "Mixed"
    #   },
    #   "rid": "ri.phonograph2-objects.main.object.8d6c23f0-2015-451e-a6ce-cad6637eb23c"
    # }
    response: List[Dict] = ontocall(path)
    if path == 'objectTypes':
      apiNames = sorted([t['apiName'] for t in response if t['apiName'].startswith('OMOP')])
      return apiNames

    return {'unrecognized path': path}
    # dict_rows: List[Dict] = [x['properties'] for x in response]
    # return dict_rows
# todo: figure out what is the advantage of declaring 'endpoint'
# api.add_resource(OntoCall, '/ontocall', endpoint='ontocall')
api.add_resource(OntoCall, '/ontocall/<path:path>')

