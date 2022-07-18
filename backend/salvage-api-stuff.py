import os
from typing import Dict


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
