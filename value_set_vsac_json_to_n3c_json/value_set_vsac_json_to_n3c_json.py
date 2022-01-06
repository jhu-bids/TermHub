"""Main module
# resources
- http://hl7.org/fhir/valueset.html
- Example sheet: https://docs.google.com/spreadsheets/d/1yopYzXbMG-4Fo6q6_bCaIcb9SUEfGUd_F8EHa7-IUcs/edit#gid=0
# to-do's
1. auto-gen curl commands for upload
  - a. include json explicitly in string, or
  - b. link to file
2. fhir bundle, instead of multiple json files
"""
import json
from copy import copy
from typing import Dict, Any, List

import pandas as pd


# to-do: Move to constants?
# commented out fields are optional
JSON_TEMPLATE: Dict[str, Any] = {
    "resourceType": "ValueSet",  # not defined in http://hl7.org/fhir/valueset.html
    "id": "TO_FILL",  # not defined in http://hl7.org/fhir/valueset.html
    "meta": {  # not defined in http://hl7.org/fhir/valueset.html
        "profile": [
          "http://hl7.org/fhir/StructureDefinition/shareablevalueset"
        ]
    },
    "text": {  # not defined in http://hl7.org/fhir/valueset.html
        "status": "generated",
        "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t\t<p>{}</p>\n\t\t</div>"
    },
    "url": "http://n3cValueSets.org/fhir/ValueSet/{}",  # can format w/ id  # optional?
    # "identifier": [
    #   {
    #     "system": "e.g. http://acme.com/identifiers/valuesets",
    #     "value": "e.g. loinc-cholesterol-int"
    #   }
    # ],
    # "version": "e.g. 1",
    "name": "TO_FILL",  # Name for this value set (computer friendly)
    "title": "TO_FILL",  # Name for this value set (human friendly)
    "status": "TO_FILL",  # draft | active | retired | unknown
    # "experimental": True,
    # "date": "2015-06-22",
    # "publisher": "e.g. HL7 International",
    # "contact": [
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
    "description": "TO_FILL",  # optional
    # "useContext": [
    #   {
    #     "code": {
    #       "system": "e.g. http://terminology.hl7.org/CodeSystem/usage-context-type",
    #       "code": "e.g. age"
    #     },
    #     "valueQuantity": {  # example
    #       "value": 18,
    #       "comparator": ">",
    #       "unit": "yrs",
    #       "system": "http://unitsofmeasure.org",
    #       "code": "a"
    #     }
    #   }
    # ],
    # "jurisdiction": [
    #   {
    #     "coding": [
    #       {
    #         "system": "e.g. urn:iso:std:iso:3166",
    #         "code": "US"
    #       }
    #     ]
    #   }
    # ],
    # "purpose": "e.g. This value set was published by ACME Inc in order to make clear which codes are used for...",
    # "copyright": "e.g. This content from LOINC ® is...",  # not defined in http://hl7.org/fhir/valueset.html
    "compose": {
        # "lockedDate": "e.g 2012-06-13",
        # "inactive": True,
        "include": [
            {
                "system": "TO_FILL",  # e.g. http://loinc.org
                "version": "TO_FILL",  # e.g. 2.36
                "concept": [  # examples below
                    # {
                    #   "code": "14647-2",
                    #   "display": "Cholesterol [Moles/Volume]"
                    # },
                    # {
                    #   "code": "2093-3",
                    #   "display": "Cholesterol [Mass/Volume]"
                    # },
                ]
            }
        ]
    }
}


def run(file_path: str, indent=4):
    """Main function

    Args:
        file_path (str): Path to file
        indent (int): If 0, there will be no line breaks and no indents. Else,
        ...you get both.
    """
    df: pd.DataFrame = pd.read_csv(file_path)

    # Populate JSON objs
    d_list: List[Dict] = []
    valueset_ids: List[str] = list(df['valueSet.id'].unique())
    for valueset_id in valueset_ids:
        df_i = df[df['valueSet.id'] == valueset_id]
        d: Dict = copy(JSON_TEMPLATE)
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
        print()

    # Save file
    for d in d_list:
        valueset_name = d['name']
        with open(valueset_name + '.json', 'w') as fp:
            if indent:
                json.dump(d, fp, indent=indent)
            else:
                json.dump(d, fp)

    print()
