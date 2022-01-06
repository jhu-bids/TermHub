"""Main module
# Resources
- Reference google sheets:
  https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
  https://docs.google.com/spreadsheets/d/1uroJbhMmOTJqRkTddlSNYleSKxw4i2216syGUSK7ZuU/edit?userstoinvite=joeflack4@gmail.com&actionButton=1#gid=435465078
"""
import json
from copy import copy
from typing import Dict, List

from value_set_vsac_json_to_n3c_json.definitions.constants import JSON_TEMPLATE
from value_set_vsac_json_to_n3c_json.google_sheets import get_sheets_data
from value_set_vsac_json_to_n3c_json.vsac_api import get_service_ticket, get_ticket_granting_ticket


def run(file_path: str, indent=4):
    """Main function

    Args:
        file_path (str): Path to file
        indent (int): If 0, there will be no line breaks and no indents. Else,
        ...you get both.
    """
    # 1. Get OIDs to query
    # TODO: Get a different API_Key for this than my 'ohbehave' project
    xxx = get_sheets_data()

    # 2. Get VSAC auth ticket
    tgt = get_ticket_granting_ticket()
    service_ticket = get_service_ticket(tgt)


    # TODO:
    # TODO 1: do from xml if can't do json
    # Populate JSON objs
    d_list: List[Dict] = []
    valueset_ids: List[str] = []
    for valueset_id in valueset_ids:
        df_i = {}
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
