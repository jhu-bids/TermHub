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
from typing import Dict, Any, List, Union

import pandas as pd


def upload(d_list: List[Dict], upload_url: str) -> str:
    """Upload to FHIR server"""
    # TODO: If upload_url is a server, add /fhir/ValueSet to url
    #  ...and maybe do a try/except just in case was overzealous in assuming their first url wasnt a real endpoint?
    response_json: str = ''
    print(d_list, upload_url)
    return response_json


def save_json(d_list: List[Dict], json_indent=4):
    """Save JSON"""
    # TODO: Mkdir
    for d in d_list:
        valueset_name = d['name']
        with open(valueset_name + '.json', 'w') as fp:
            if json_indent:
                json.dump(d, fp, indent=json_indent)
            else:
                json.dump(d, fp)


def get_json_custom1(input_file_path: str) -> List[Dict[str, Any]]:
    """TODO: placeholder; remove this func and control logic in run() later - Joe 2022/02/08"""
    df: pd.DataFrame = pd.read_csv(input_file_path)
    d_list: List[Dict] = []
    valueset_ids: List[str] = list(df['valueSet.id'].unique())
    for valueset_id in valueset_ids:
        df_i = df[df['valueSet.id'] == valueset_id]
        d: Dict[str, Any] = {}
        d['id'] = int(df_i['valueSet.id'][0])
        d['text']['div'] = d['text']['div'].format(df_i['valueSet.description'][0])
        d['url'] = d['url'].format(str(df_i['valueSet.id'][0]))
        d['name'] = df_i['valueSet.name'][0]
        d['title'] = df_i['valueSet.name'][0]
        d['status'] = df_i['valueSet.status'][0]
        d['description'] = df_i['valueSet.description'][0]
        d['compose']['include'][0]['system'] = df_i['valueSet.codeSystem'][0]
        d['compose']['include'][0]['version'] = df_i['valueSet.codeSystemVersion'][0]
        concepts = []
        for index, row in df_i.iterrows():
            concepts.append({
                'code': row['concept.code'],
                'display': row['concept.display']
            })
        d['compose']['include'][0]['concept'] = concepts
        d_list.append(d)

    return d_list


def get_palantir_concept_set_tables(input_file_path: List[str]) -> List[Dict[str, Any]]:
    """get_palantir_concept_set_tables JSON dicts"""
    # Vars
    valueset_id_fld = 'codeset_id'

    # Read and validate files
    df_list: List[pd.DataFrame] = [pd.read_csv(p) for p in input_file_path]
    code_sets_df: pd.DataFrame
    concepts_df: pd.DataFrame
    err = 'CSVs do not have expected field names. For the code_sets table, at least the field "concept_set_name" is ' \
          'expected. For the concept members table, at least the field "code" is expected. Either 1 or both of the' \
          'supplied CSVs did not have these expected fields.'
    for df in df_list:
        if 'concept_set_name' in df.columns:
            code_sets_df = df
        elif 'code' in df.columns:
            concepts_df = df
    # noinspection PyUnboundLocalVariable
    if code_sets_df.empty or concepts_df.empty:
        raise RuntimeError(err)

    # Construct JSON dictionaries
    d_list: List[Dict] = []
    valueset_ids: List[str] = list(code_sets_df[valueset_id_fld].unique())
    for valueset_id in valueset_ids:
        code_sets_df_i = code_sets_df[code_sets_df[valueset_id_fld] == valueset_id]
        d: Dict[str, Any] = {}

        # TODO: valueSet fields. use code_sets_df_i for fields at the code_set level
        d["resourceType"] = "ValueSet",  # not defined in http://hl7.org/fhir/valueset.html
        # "meta": {  # not defined in http://hl7.org/fhir/valueset.html
        #     "profile": [
        #         "http://hl7.org/fhir/StructureDefinition/shareablevalueset"
        #     ]
        # },
        d['id'] = int(valueset_id)  # not defined in http://hl7.org/fhir/valueset.html
        d["url"] = f"http://n3cValueSets.org/fhir/ValueSet/{valueset_id}"
        # "name": "TO_FILL",  # Name for this value set (computer friendly)
        # "title": "TO_FILL",  # Name for this value set (human friendly)
        # "status": "TO_FILL",  # draft | active | retired | unknown
        # "description": "TO_FILL",  # optional
        # "purpose":  "TO_FILL" # (we can take this from the 'intention' field)

        # TODO: concept fields taken from concepts_df_i
        concepts = []
        concepts_df_i = concepts_df[concepts_df[valueset_id_fld] == valueset_id]
        for index, row in concepts_df_i.iterrows():
            # "compose": {
            #     "include": [
            #         {
            #             "system": "TO_FILL",  # e.g. http://loinc.org
            #             "version": "TO_FILL",  # e.g. 2.36
            #             "concept": [  # examples below
            #                 # {
            #                 #   "code": "14647-2",
            #                 #   "display": "Cholesterol [Moles/Volume]"
            #                 # },
            #             ]
            #         }
            #     ]
            # }
            concepts.append({
                'code': row['concept.code'],  # TODO: change to actual field
                'display': row['concept.display']  # TODO: change to actual field
            })
        # TODO: Don't do this 0 thing. actually filter systems found and
        #  include system etc and iterate over. This can be done by getting the unique() values
        #  of code systems found in concepts_df_i.
        d['compose']['include'][0]['concept'] = concepts

        d_list.append(d)

    return d_list


def run(
    input_file_path: Union[str, List[str]], input_schema_format: str, output_json: bool, upload_url: str, json_indent=4
) -> List[Dict]:
    """Main function"""
    # Get JSON dicts
    d_list: List[Dict]
    if input_schema_format == 'custom1':
        d_list = get_json_custom1(input_file_path)  # TODO: placeholder to remove
    elif input_schema_format == 'palantir-concept-set-tables':
        d_list = get_palantir_concept_set_tables(input_file_path)  # TODO

    # Return & side effects
    if output_json:
        # noinspection PyUnboundLocalVariable
        save_json(d_list, json_indent)  # TODO
    if upload_url:
        upload(d_list, upload_url)  # TODO

    return d_list
