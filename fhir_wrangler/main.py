"""Main module
# Resources
- http://hl7.org/fhir/valueset.html
"""
import os
from typing import Dict, List

import pandas as pd
import requests


# Vars
PACKAGE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)))
PROJECT_DIR = os.path.join(PACKAGE_DIR, '..')
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
DB_CSV_PATH = os.path.join(DATA_DIR, 'cset.csv')


# Functions
def _delete_nonauthoritative_value_sets(urls: List[str]):
    """"Deletes non-authoritative value sets"""
    # TODO: read cset and get ids
    # Find authortative value set IDs
    df: pd.DataFrame = pd.read_csv(DB_CSV_PATH)
    authoritative_ids = [str(x) for x in df['internal_id']]
    authoritative_fhir_ids = ['a' + x for x in authoritative_ids]
    authoritative_all_ids: List[str] = authoritative_ids + authoritative_fhir_ids  # combine them just in case in future we don't need the leading 'a'
    authoritative_all_ids.sort()

    # Delete anything not in
    for base_url in urls:
        get_url = base_url
        value_sets_json_list: List[Dict] = []
        while True:
            value_sets_json: Dict = requests.get(get_url).json()
            value_sets_json_list.append(value_sets_json)
            pagination_cursor: Dict = value_sets_json['link'][1]
            if pagination_cursor['relation'] != 'next':  # no more pages remain
                break
            get_url = pagination_cursor['url']

        value_sets_ids: List[str] = []
        for page in value_sets_json_list:
            entries = page['entry']
            for entry in entries:
                this_id = entry['resource']['id']
                value_sets_ids.append(this_id)
        # TODO: only ~288 codes, 1-288 in value_set_ids. Why aren't the ones I assigned showing up? Do they have 2 ids?
        # TODO: ahh, i think this is because they were all auto-assigned before i did the manual assignment. i should
        #  delete and re-upload all of them, then rerun this tool again to check. if works, nothing shoudl be
        #  deleted on the second go around

        # TODO: I think code is done now; i should run and check
        to_delete: List[str] = [x for x in value_sets_ids if x not in authoritative_ids]
        for vset_id in to_delete:
            delete_url = base_url + '/' + vset_id
            requests.delete(delete_url)


def run(
    url: List[str], delete_nonauthoritative_value_sets=False
):
    """Main function"""
    if delete_nonauthoritative_value_sets:
        _delete_nonauthoritative_value_sets(url)
