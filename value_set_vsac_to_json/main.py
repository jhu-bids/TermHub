"""Main module
# Resources
- Reference google sheets:
  https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
  https://docs.google.com/spreadsheets/d/1uroJbhMmOTJqRkTddlSNYleSKxw4i2216syGUSK7ZuU/edit?userstoinvite=joeflack4@gmail.com&actionButton=1#gid=435465078
"""
import json
from copy import copy
from datetime import datetime
from typing import Dict, List, OrderedDict

import pandas as pd

from value_set_vsac_to_json.definitions.constants import FHIR_JSON_TEMPLATE, OMOP_JSON_TEMPLATE
from value_set_vsac_to_json.google_sheets import get_sheets_data
from value_set_vsac_to_json.vsac_api import get_ticket_granting_ticket, get_value_set, get_value_sets


# TODO: repurpose this to use VSAC format
def vsac_to_fhir(value_set: Dict) -> Dict:
    """Convert VSAC JSON dict to FHIR JSON dict"""
    d: Dict = copy(FHIR_JSON_TEMPLATE)
    d['id'] = int(value_set['valueSet.id'][0])
    d['text']['div'] = d['text']['div'].format(value_set['valueSet.description'][0])
    d['url'] = d['url'].format(str(value_set['valueSet.id'][0]))
    d['name'] = value_set['valueSet.name'][0]
    d['title'] = value_set['valueSet.name'][0]
    d['status'] = value_set['valueSet.status'][0]
    d['description'] = value_set['valueSet.description'][0]
    d['compose']['include'][0]['system'] = value_set['valueSet.codeSystem'][0]
    d['compose']['include'][0]['version'] = value_set['valueSet.codeSystemVersion'][0]
    concepts = []
    d['compose']['include'][0]['concept'] = concepts

    return d


# TODO:
def vsac_to_omop(v: Dict) -> Dict:
    """Convert VSAC JSON dict to OMOP JSON dict"""

    # Attempt at regexp
    # Clinical Focus: Asthma conditions which suggest applicability of NHLBI NAEPP EPR3 Guidelines for the Diagnosis and Management of Asthma (2007) and the 2020 Focused Updates to the Asthma Management Guidelines),(Data Element Scope: FHIR Condition.code),(Inclusion Criteria: SNOMEDCT concepts in "Asthma SCT" and ICD10CM concepts in "Asthma ICD10CM" valuesets.),(Exclusion Criteria: none)
    # import re
    # regexer = re.compile('\((.+): (.+)\)')  # fail
    # regexer = re.compile('\((.+): (.+)\)[,$]')
    # found = regexer.match(v['ns0:Purpose'])
    # x1 = found.groups()[0]

    purposes = v['ns0:Purpose'].split('),')
    d = {
        "Concept Set Name": v['@displayName'],
        "Created At": 'vsacToOmopConversion:{}; vsacRevision:{}'.format(
            datetime.now().strftime('%Y/%m/%d'),
            v['ns0:RevisionDate']),
        "Created By": v['ns0:Source'],
        # "Created By": "https://github.com/HOT-Ecosystem/ValueSet-Converters",
        "Intention": {
            "Clinical Focus": purposes[0].split('(Clinical Focus: ')[1],
            "Inclusion Criteria": purposes[0].split('(Inclusion Criteria: ')[1],
            "Data Element Scope": purposes[0].split('(Data Element Scope: ')[1],
            "Exclusion Criteria": purposes[0].split('(Exclusion Criteria: ')[1],
        },
        "Limitations": {
            "Exclusion Criteria": "",
            "VSAC Note": None,  # VSAC Note: (exclude if null)
        },
        "Provenance": {
            "VSAC Steward": "",
            "OID": "",
            "Code System(s)": [],
            "Definition Type": "",
            "Definition Version": "",
        }
    }

    return d


def run(format=['fhir', 'omop'][1], indent=4) -> List[Dict]:
    """Main function

    Args:
        file_path (str): Path to file
        indent (int): If 0, there will be no line breaks and no indents. Else,
        ...you get both.
    """
    # 1. Get OIDs to query
    # TODO: Get a different API_Key for this than my 'ohbehave' project
    df: pd.DataFrame = get_sheets_data()
    object_ids: List[str] = [x for x in list(df['OID']) if x != '']

    # 2. Get VSAC auth ticket
    tgt: str = get_ticket_granting_ticket()
    # service_ticket = get_service_ticket(tgt)

    value_sets_dict: OrderedDict = get_value_sets(object_ids, tgt)
    value_sets: List[OrderedDict] = value_sets_dict['ns0:RetrieveMultipleValueSetsResponse']['ns0:DescribedValueSet']

    # Populate JSON objs
    d_list: List[Dict] = []
    for value_set in value_sets:
        value_set2 = {}
        if format == 'fhir':
            value_set2 = vsac_to_fhir(value_set)
        elif format == 'omop':
            value_set2 = vsac_to_omop(value_set)
        d_list.append(value_set2)

    # Save file
    for d in d_list:
        valueset_name = d['name']
        with open(valueset_name + '.json', 'w') as fp:
            if indent:
                json.dump(d, fp, indent=indent)
            else:
                json.dump(d, fp)

    return d_list
