"""Main module
# TODO's:
- For mappings, I believe Amin will be providing us to .parquet files. We can read with pandas: https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html

Resources
- Validate URL (for testing POSTs without it actually taking effect): https://unite.nih.gov/actions/api/actions/validate
# TODO: Update wiki article to be up-to-date with correct params for 'concept set version':
- Wiki article on how to create these JSON: https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs
"""
import json
import os
from datetime import datetime, timezone

import requests
import pandas as pd

from enclave_wrangler.config import config
from enclave_wrangler.enclave_api import get_cs_container_data
from enclave_wrangler.enclave_api import get_cs_version_data
from enclave_wrangler.utils import log_debug_info


DEBUG = True
# PALANTIR_ENCLAVE_USER_ID_1: This is an actual ID to a valid user in palantir, who works on our BIDS team.
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
VSAC_LABEL_PREFIX = '[VSAC Bulk-Import test1] '
# API_URL query params:
# 1. ?synchronousPropagation=false: Not sure what this does or if it helps.
API_URL = 'https://unite.nih.gov/actions/api/actions'
# Based on curl usage, it seems that '?synchronousPropagation=false' is not required
# API_VALIDATE_URL = 'https://unite.nih.gov/actions/api/actions/validate'
API_VALIDATE_URL = 'https://unite.nih.gov/actions/api/actions/validate?synchronousPropagation=false'


def _datetime_palantir_format() -> str:
    """Returns datetime str in format used by palantir data enclave
    e.g. 2021-03-03T13:24:48.000Z (milliseconds allowed, but not common in observed table)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'


def run(input_csv_folder_path):
    """Main function"""
    # TODO: Create 3 JSON structures per concept set and link them on ID
    ## 1. container
    concept_set_container_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    # concept_set_version_item_rv_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')

    concept_set_container_edited_json_all_rows = []
    code_set_version_json_all_rows = []
    # concept_set_container_version_all_rows = []
    # concept_set_container_code_expression_all_rows = []
    for index, row in concept_set_container_edited_df.iterrows():
        cs_name = row['concept_set_name']
        single_row = get_cs_container_data(row['concept_set_name'])
        concept_set_container_edited_json_all_rows.append(single_row)


    for index, row in code_sets_df.iterrows():
        cs_id = row['codeset_id']
        cs_name = row['concept_set_name']
        cs_intention = row['intention']
        cs_limitations = row['limitations']
        cs_update_msg = row['update_message']
        cs_status = row['status']
        cs_provenance = row['provenance']
        single_row = get_cs_version_data(cs_name, cs_id, cs_intention, cs_limitations, cs_update_msg, cs_provenance)
        # cs_name, cs_id, intension, limitation, update_msg, status, provenance
        code_set_version_json_all_rows.append(single_row)

    # Do a test first using 'valdiate'
    api_url = API_VALIDATE_URL
    test_data_dict = concept_set_container_edited_json_all_rows[0]
    header = {
        "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        'content-type': 'application/json'
    }
    if DEBUG:
        log_debug_info()
    response = requests.post(
        api_url,
        data=json.dumps(test_data_dict),
        headers=header)
    response_json = response.json()
    ## TODO : validate all three calls before calling the acutal APIs. successfully validated results
    ## {'type': 'validResponse', 'validResponse':
    ## {'results':
    ## {'ri.actions.main.validation-rule.fe2770c2-3600-4dd7-b59c-b38f47ad122a': { ...}}}
    print(response_json)

    # TODO: After successful validate, do real POSTs (check if they exist first?
    # TODO: after the action POST check for successful return code before calling the 2nd api
    ## {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Conjure:UnprocessableEntity', 'errorInstanceId': 'c3eefa5a-61b9-45fc-aaa7-30355c15c92b', 'parameters': {}}

    ##TODO: if type returned is 'validResponse' then continue checking for the 2nd POST call to createNewDraftConceptSetVersion()
    api_url = API_VALIDATE_URL
    header = {
        "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        'content-type': 'application/json'}
    cs_version_data_dict = code_set_version_json_all_rows[0]
    if DEBUG:
        log_debug_info()
    response = requests.post(api_url, data=json.dumps(cs_version_data_dict), headers=header)
    response_json = response.json()
    print(response_json)

    return response_json

if __name__ == '__main__':
    run(None)
