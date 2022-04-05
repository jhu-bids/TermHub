"""Main module
# Resources
- http://hl7.org/fhir/valueset.html
- Example sheet: https://docs.google.com/spreadsheets/d/1Vxx0EXxSk8shxEWybVP68quCG4oey1vwoWvhADQjkek
# to-do's
1. auto-gen curl commands for upload
  - a. include json explicitly in string, or
  - b. link to file
2. fhir bundle, instead of multiple json files
3. Add following fields?
    # "contact": [  # do we have a BIDS email? or want to use?
    #   {
    #     "name": "e.g. FHIR project team",
    #     "telecom": [
    #       {
    #         "system": "url",
    #         "value": "http://hl7.org/fhir"
    #       }
    #     ]
    #   }
    # ],
    # "version": "e.g. 1",  # JOIN on other table/CSV to get?
    # "experimental": True,  # how to determine?
    # auto-generated?:
    "text": {  # not defined in http://hl7.org/fhir/valueset.html
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t\t<p>{}</p>\n\t\t</div>"
    },
    # "date": "2015-06-22",  # Date of what? Upload? initial create? last update?
    # "publisher": "e.g. HL7 International",
"""
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Union

from numpy import int64
import pandas as pd
import requests


# todo: Should verify that I have the best canonical reference URLs for each vocabulary.
SYSTEM_URI_MAP = {
    'icd9cm': 'http://purl.bioontology.org/ontology/ICD9CM',
    'icd9': 'http://purl.bioontology.org/ontology/ICD9CM',
    'icd10cm': 'http://purl.bioontology.org/ontology/ICD10CM',
    'icd10': 'http://purl.bioontology.org/ontology/ICD10CM',
    'icd11cm': 'http://purl.bioontology.org/ontology/ICD11CM',
    'icd11': 'http://purl.bioontology.org/ontology/ICD11CM',
    'icd9pcs': 'http://purl.bioontology.org/ontology/ICD9PCS',
    'icd10pcs': 'http://purl.bioontology.org/ontology/ICD10PCS',
    'icd11pcs': 'http://purl.bioontology.org/ontology/ICD11PCS',
    'snomed': 'http://snomed.info/sct',
    'snomedct': 'http://snomed.info/sct',
    'cpt': 'https://bioportal.bioontology.org/ontologies/CPT',
    'hcpcs': 'https://www.cms.gov/Medicare/Coding/MedHCPCSGenInfo/HCPCSCODINGPROCESS',
    'hcpcslevel2': 'https://www.cms.gov/Medicare/Coding/MedHCPCSGenInfo/HCPCSCODINGPROCESS',
    'hcpcslevelii': 'https://www.cms.gov/Medicare/Coding/MedHCPCSGenInfo/HCPCSCODINGPROCESS',
    'loinc': 'http://purl.bioontology.org/ontology/LOINC',
    'rxnorm': 'http://purl.bioontology.org/ontology/RXNORM/',
}
PACKAGE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)))
PROJECT_DIR = os.path.join(PACKAGE_DIR, '..')
CACHE_DIR = os.path.join(PACKAGE_DIR, 'cache')


# Functions
def _get_output_dirname(path: str = None) -> str:
    """Get directory name for this cache"""
    if path:
        return path.replace('/', '-').replace('\\,', '')
    return str(datetime.now()).replace(':', '-')[:19]


def upload(d_list: List[Dict], upload_urls: List[str]):
    """Upload to FHIR server"""
    for base_url in upload_urls:
        for d in d_list:
            # Reason for adding ID to url: https://www.hl7.org/fhir/http.html#update
            url = f'{base_url}/{d["id"]}'
            response = requests.put(url, json=d)
            # Codes 400+ are errors
            if int(response.status_code) >= 400 and int(response.status_code) != 422:
                raise RuntimeError(
                    f'Got error {response.status_code} when uploading item with ID {d["id"]} to {url}: \n'
                    f'{response.text}')
            # Unprocessable Entity: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422
            if int(response.status_code) == 422:
                err_list = [x['diagnostics'] for x in json.loads(response.text)['issue']]
                err = err_list[0] if len(err_list) == 1 else str(err_list)
                print(err, file=sys.stderr)


def save_json(d_list: List[Dict], input_path=None, output_json=False, use_cache=False, json_indent=4) -> str:
    """Save JSON"""
    outdir = os.path.join(PROJECT_DIR, _get_output_dirname())
    cache_outdir = os.path.join(CACHE_DIR, _get_output_dirname(input_path))

    if output_json and not os.path.exists(outdir):
        os.makedirs(outdir)
    if use_cache and not os.path.exists(cache_outdir):
        os.makedirs(cache_outdir)

    for d in d_list:
        filename = d['id'] + '.json'
        filepaths = []
        if output_json:
            filepaths.append(os.path.join(outdir, filename))
        if use_cache:
            filepaths.append(os.path.join(cache_outdir, filename))
        for path in filepaths:
            with open(path, 'w') as file:
                json.dump(d, file, indent=json_indent)

    return outdir


def get_palantir_concept_set_tables(input_dir_path: List[str]) -> List[Dict[str, Any]]:
    """get_palantir_concept_set_tables JSON dicts
    https://build.fhir.org/valueset.html
    todo: concept_set_container_edited.csv: Right now we're just using code_sets.csv, but in the future, it might be
     useful to also read in concept_set_container_edited.csv, especially if as an export from the enclave, because it
     might have data that is not in code_sets.csv.
    """
    # Vars
    valueset_id_fld = 'codeset_id'
    system_uri_warning = \
        'Code system with label "{}" not found in local `SYSTEM_URI_MAP`. FHIR asks for that URIs should be ' \
        'provided, but in lieu of that, the label will be used in this case.'
    # Why PyCharm TypeChecker warning? - Joe 2022/04/06
    # noinspection PyTypeChecker
    code_sets_df: pd.DataFrame = pd.read_csv(os.path.join(input_dir_path, 'code_sets.csv'))
    # noinspection PyTypeChecker
    concepts_df: pd.DataFrame = pd.read_csv(os.path.join(input_dir_path, 'concept_set_version_item_rv_edited.csv'))

    # Construct JSON dictionaries
    d_list: List[Dict] = []
    valueset_ids: List[str] = list(code_sets_df[valueset_id_fld].unique())
    for valueset_id in valueset_ids:
        # HAPI / fhir requires assigned IDs to have at least one non-numeric char:
        assigned_id = 'a' + str(valueset_id) if type(valueset_id) in [int, int64] else valueset_id
        code_sets_df_i = code_sets_df[code_sets_df[valueset_id_fld] == valueset_id]
        # There should not be are multiple instances, but just in case, we'll take the first row:
        cset_csv: Dict = code_sets_df_i.to_dict('records')[0]
        cset_json: Dict[str, Any] = {}
        cset_json['resourceType'] = 'ValueSet'  # not defined in http://hl7.org/fhir/valueset.html
        cset_json['id'] = assigned_id  # not defined in http://hl7.org/fhir/valueset.html
        cset_json['url'] = f'http://n3cValueSets.org/fhir/ValueSet/{valueset_id}'
        cset_json['name'] = cset_csv['concept_set_name']  # Name for this value set (computer friendly)
        cset_json['title'] = cset_csv['concept_set_name']  # Name for this value set (human friendly)
        cset_json['status'] = 'active'  # draft | active | retired | unknown
        cset_json['description'] = json.dumps({
            'limitations': cset_csv['limitations'],
            'provenance': cset_csv['provenance']
        })  # `description` is optional
        cset_json['purpose'] = cset_csv['intention']
        cset_json['compose'] = {}

        system_concepts = {}
        concepts_df_i = concepts_df[concepts_df[valueset_id_fld] == valueset_id]
        for index, concept in concepts_df_i.iterrows():
            concept = dict(concept)
            system_label = concept['codeSystem']
            if system_label not in system_concepts:
                system_label_stripped = system_label.replace('-', '').replace('_', '').replace(' ', '').lower()
                system_uri = SYSTEM_URI_MAP.get(system_label_stripped, system_label)
                if system_uri == system_label:
                    print(system_uri_warning.format(system_label), file=sys.stderr)
                system_concepts[system_label] = {
                    'system': system_uri,  # URI
                    # 'version': ''  # optional; ideal to include, but this info isn't available from this source
                    'concept': []
                }
            system_concepts[system_label]['concept'].append({
                'code': concept['code'],
                'display': f'{system_label}:{concept["code"]}'  # TODO: get label by looking up in local code systems?
            })
        cset_json['compose']['include'] = [x for x in list(system_concepts.values())]

        d_list.append(cset_json)

    return d_list


# noinspection PyUnusedLocal
def get_vsac_value_sets(oids: List[str]) -> List[dict]:
    """useful info about getting multiple gets at once: https://stackoverflow.com/a/66874788/1368860
    I tested and doesn;t seem to work w/ VSAC's fhir api - joeflack 2022/02
    """
    pass


# TODO: test this out
def read_from_local_json(input_dir_path) -> List[Dict]:
    """Read from local JSON. one use case is for for cached data."""
    cache_inner_dirname = _get_output_dirname(input_dir_path)
    cache_path = os.path.join(CACHE_DIR, cache_inner_dirname)

    d_list: List[Dict] = []
    if os.path.isdir(cache_path):
        d_list = [json.load(open(os.path.join(cache_path, x))) for x in os.listdir(cache_path)]

    return d_list


def run(
    input_path: Union[str, List[str]], input_schema_format: str, output_json: bool, upload_url: List[str],
    use_cache=False, json_indent=4
) -> List[Dict]:
    """Main function"""
    # Get JSON dicts
    d_list: List[Dict] = []
    if use_cache:
        d_list = read_from_local_json(input_path)
    if not d_list:
        if input_schema_format == 'palantir-concept-set-tables':
            d_list = get_palantir_concept_set_tables(input_path)
        else:
            raise NotImplementedError

    # Return & side effects
    if output_json or use_cache:
        # noinspection PyUnboundLocalVariable
        save_json(d_list, input_path, output_json, use_cache, json_indent)  # TODO
    if upload_url:
        upload(d_list, upload_url)

    return d_list
