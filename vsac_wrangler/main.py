"""Main module
# Resources
- Reference google sheets:
  - Source data: https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=1335629675
  - Source data (old): https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
  - Output example: https://docs.google.com/spreadsheets/d/1uroJbhMmOTJqRkTddlSNYleSKxw4i2216syGUSK7ZuU/edit?userstoinvite=joeflack4@gmail.com&actionButton=1#gid=435465078
"""
import json
import os
import pickle
from copy import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, OrderedDict

import pandas as pd

from vsac_wrangler.config import CACHE_DIR, OUTPUT_DIR
from vsac_wrangler.definitions.constants import FHIR_JSON_TEMPLATE
from vsac_wrangler.google_sheets import get_sheets_data
from vsac_wrangler.vsac_api import get_ticket_granting_ticket, get_value_sets


# TODO: repurpose this to use VSAC format
# noinspection DuplicatedCode
def vsac_to_fhir(value_set: Dict) -> Dict:
    """Convert VSAC JSON dict to FHIR JSON dict"""
    # TODO: cop/paste FHIR_JSON_TEMPLATE literally here instead and use like other func
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
def vsac_to_vsac(v: Dict, depth=2) -> Dict:
    """Convert VSAC JSON dict to OMOP JSON dict
    This is the format @DaveraGabriel specified by looking at the VSAC web interface."""
    # Attempt at regexp
    # Clinical Focus: Asthma conditions which suggest applicability of NHLBI NAEPP EPR3 Guidelines for the Diagnosis and
    # Management of Asthma (2007) and the 2020 Focused Updates to the Asthma Management Guidelines),(Data Element Scope:
    # FHIR Condition.code),(Inclusion Criteria: SNOMEDCT concepts in "Asthma SCT" and ICD10CM concepts in "Asthma
    # ICD10CM" valuesets.),(Exclusion Criteria: none)
    # import re
    # regexer = re.compile('\((.+): (.+)\)')  # fail
    # regexer = re.compile('\((.+): (.+)\)[,$]')
    # found = regexer.match(value_sets['ns0:Purpose'])
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
            "Steward": "",
            "OID": "",
            "Code System(s)": [],
            "Definition Type": "",
            "Definition Version": "",
        }
    }
    # TODO: use depth to make this either nested JSON, or, if depth=1, concatenate
    #  ... all intention sub-fields into a single string, etc.
    if depth == 1:
        d['Intention'] = ''
    elif depth < 1 or depth > 2:
        raise RuntimeError(f'vsac_to_vsac: depth parameter valid range: 1-2, but depth of {depth} was requested.')

    return d


def get_csv(
    value_sets: List[OrderedDict], field_delimiter=',', code_delimiter='|'
) -> pd.DataFrame:
    """get a list of codes"""
    rows = []
    for value_set in value_sets:
        name = value_set['@displayName']
        purposes = value_set['ns0:Purpose'].split('),')
        code_system_codes = {}
        for concept_dict in value_set['ns0:ConceptList']['ns0:Concept']:
            code = concept_dict['@code']
            code_system = concept_dict['@codeSystemName']
            if code_system not in code_system_codes:
                code_system_codes[code_system] = []
            code_system_codes[code_system].append(code)

        for code_system, codes in code_system_codes.items():
            purposes2 = []
            for p in purposes:
                i1 = 1 if p.startswith('(') else 0
                i2 = -1 if p[len(p) - 1] == ')' else len(p)
                purposes2.append(p[i1:i2])
            row = {
                'name': name,
                'nameVSAC': '[VSAC] ' + name,
                'oid': value_set['@ID'],
                'codeSystem': code_system,
                'limitations': purposes2[3],
                'intention': '; '.join(purposes2[0:3]),
                'provenance': '; '.join([
                    'Steward: ' + value_set['ns0:Source'],
                    'OID: ' + value_set['@ID'],
                    'Code System(s): ' + ','.join(list(code_system_codes.keys())),
                    'Definition Type: ' + value_set['ns0:Type'],
                    'Definition Version: ' + value_set['@version'],
                    'Accessed: ' + str(datetime.now())[0:-7]
                ]),
            }
            if len(codes) < 2000:
                row['codes'] = code_delimiter.join(codes)
            else:
                row['codes'] = code_delimiter.join(codes[0:1999])
                if len(codes) < 4000:
                    row['codes2'] = code_delimiter.join(codes[2000:])
                else:
                    row['codes2'] = code_delimiter.join(codes[2000:3999])
                    row['codes3'] = code_delimiter.join(codes[4000:])

            rows.append(row)

    # Create/Return DF & Save CSV
    df = pd.DataFrame(rows)
    outdir = os.path.join(OUTPUT_DIR, datetime.now().strftime('%Y.%m.%d'))
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    output_format = 'csv' if field_delimiter == ',' else 'tsv' if field_delimiter == '\t' else 'txt'
    outpath = os.path.join(outdir, f'list_of_codes.{output_format}')
    df.to_csv(outpath, sep=field_delimiter, index=False)

    return df


def run(
    output_format=['tabular/csv', 'json'][0],
    output_structure=['fhir', 'vsac'][1],
    field_delimiter=[',', '\t'][0],  # TODO: add to cli
    intra_field_delimiter=[',', ';', '|'][2],  # TODO: add to cli
    json_indent=4, use_cache=False
):
    """Main function
    Refer to interfaces/cli.py for argument descriptions."""
    value_sets = []
    pickle_file = Path(CACHE_DIR, 'value_sets.pickle')

    if use_cache:
        if pickle_file.is_file() and use_cache:
            value_sets = pickle.load(open(pickle_file, 'rb'))
        else:
            use_cache = False
    if not use_cache:
        # 1. Get OIDs to query
        # TODO: Get a different API_Key for this than my 'ohbehave' project
        df: pd.DataFrame = get_sheets_data()
        object_ids: List[str] = [x for x in list(df['OID']) if x != '']

        # 2. Get VSAC auth ticket
        tgt: str = get_ticket_granting_ticket()
        # service_ticket = get_service_ticket(tgt)

        value_sets_dict: OrderedDict = get_value_sets(object_ids, tgt)
        value_sets: List[OrderedDict] = value_sets_dict['ns0:RetrieveMultipleValueSetsResponse'][
            'ns0:DescribedValueSet']

        with open(pickle_file, 'wb') as handle:
            pickle.dump(value_sets, handle, protocol=pickle.HIGHEST_PROTOCOL)

    if output_format == 'tabular/csv':
        if output_structure == 'vsac':
            get_csv(value_sets, field_delimiter, intra_field_delimiter)
        elif output_structure == 'fhir':
            raise NotImplementedError('output_structure "fhir" not available for output_format "csv/tabular".')
    elif output_format == 'json':
        # Populate JSON objs
        d_list: List[Dict] = []
        for value_set in value_sets:
            value_set2 = {}
            if output_structure == 'fhir':
                value_set2 = vsac_to_fhir(value_set)
            elif output_structure == 'vsac':
                value_set2 = vsac_to_vsac(value_set)
            d_list.append(value_set2)

        # Save file
        for d in d_list:
            valueset_name = d['name']
            with open(valueset_name + '.json', 'w') as fp:
                if json_indent:
                    json.dump(d, fp, indent=json_indent)
                else:
                    json.dump(d, fp)
