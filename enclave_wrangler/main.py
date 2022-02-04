"""Main module
# TODO's:
- For mappings, I believe Amin will be providing us to .parquet files. We can read with pandas: https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html

Resources
- Validate URL (for testing POSTs without it actually taking effect): https://unite.nih.gov/actions/api/actions/validate
# TODO: Update wiki article to be up-to-date with correct params for 'concept set version':
- Wiki article on how to create these JSON: https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs
  - CreateNewDraftOMOPConceptSetVersion: code_sets.csv
  - CreateNewConceptSet: concept_set_container_edited.csv
  - addCodeAsVersionExpression: concept_set_version_item_rv_edited.csv
"""
import json
import os
from datetime import datetime, timezone

import requests
import pandas as pd

from enclave_wrangler.config import config
from enclave_wrangler.enclave_api import get_cs_container_data
from enclave_wrangler.enclave_api import get_cs_version_data
from enclave_wrangler.enclave_api import get_cs_version_expression_data
from enclave_wrangler.enclave_api import post_request_enclave_api
from enclave_wrangler.utils import log_debug_info


# TODO: Add debug as a CLI param
DEBUG = False
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
    # TODO: Create CS container, version and itemExpressions by calling 3 REST APIs, data is submitted in JSON format

    ## 1. container
    concept_set_container_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    concept_set_version_item_rv_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')

    cs_result = pd.merge(code_sets_df, concept_set_version_item_rv_edited_df, on=['codeset_id'])

    concept_set_container_edited_json_all_rows = []
    code_set_version_json_all_rows = []
    code_set_expression_items_json_all_rows = []

    # build the list of container json data
    for index, row in concept_set_container_edited_df.iterrows():
        cs_name = row['concept_set_name']
        single_row = get_cs_container_data(row['concept_set_name'])
        concept_set_container_edited_json_all_rows.append(single_row)


    # build the list of cs version json data
    # TODO: for codeset_id, use the one in data/oid_enclaveId.csv
    # TODO: re-use for concept_set_version_item_rv_edited

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

    for index, row in code_sets_df.iterrows():
            current_code_set_id = row['codeset_id']
            # build the code and codeSystem list for the current codeSet
            # reset the code list
            code_list = []
            cs_current_code_set_df = row
            cs_name = row['concept_set_name']
            # code and code system list
            for i in range(len(concept_set_version_item_rv_edited_df)):
                if concept_set_version_item_rv_edited_df.loc[i, 'codeset_id'] == current_code_set_id:
                    code_codesystem_pair = concept_set_version_item_rv_edited_df.loc[i,'code'] + ":" + concept_set_version_item_rv_edited_df.loc[i,'codeSystem']
                    code_list.append(code_codesystem_pair)
                # print(code_list)
                exclude = concept_set_version_item_rv_edited_df.loc[i, 'isExcluded']
                descendents = concept_set_version_item_rv_edited_df.loc[i, 'includeDescendants']
                mapped = concept_set_version_item_rv_edited_df.loc[i, 'includeMapped']
                annotation = concept_set_version_item_rv_edited_df.loc[i, 'annotation']
            #now that we have the code list, generate the json for the versionExpression data
            single_row = get_cs_version_expression_data( current_code_set_id, cs_name, code_list, exclude, descendents, mapped, annotation)
            code_set_expression_items_json_all_rows.append(single_row)
    print(code_set_expression_items_json_all_rows[0])

    # Do a test first using 'valdiate'
    api_url = API_VALIDATE_URL
    header = {
        "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        'content-type': 'application/json'
    }
    if DEBUG:
        log_debug_info()

    ## validate API calls create the concept set
    ## 1. createNewConceptSet
    ## 2. createNewDraftOMOPConceptSetVersion
    ## 3. addCodeAsVersionExpression
    # TODO: We should create a function for these calls or modify existing function(s) in enclave_api.py
    #  ...in order to reduce duplicated code here. - Joe 2022/02/02
    # Validate 1: Concept set container
    test_data_dict = concept_set_container_edited_json_all_rows[0]
    respons_json = post_request_enclave_api(api_url, header, json.dumps(test_data_dict))

    #response = requests.post( api_url, data=json.dumps(test_data_dict), headers=header)
    #response_json = response.json()
    # TODO : validate all three calls before calling the acutal APIs. successfully validated results
    #  ...After the action POST check for successful return code before calling the 2nd api.
    # print(response_json)  # temp
    #if 'type' not in response_json or response_json['type'] != 'validResponse':
    #    raise SystemError(json.dumps(response_json, indent=2))

    # Validate 2: Concept set version item
    cs_version_data_dict = code_set_version_json_all_rows[0]
    # print(json.dumps(cs_version_data_dict, indent=4))  # temp
    response = requests.post(api_url, data=json.dumps(cs_version_data_dict), headers=header)
    response_json = response.json()
    # print(response_json)  # temp
    if 'type' not in response_json or response_json['type'] != 'validResponse':
        raise SystemError(json.dumps(response_json, indent=2))

    # Error: Amin says that in the backend, he's seeing error that "integer cannot be null".
    # ...It looks like this may be related to a problem on their end parsing the integer ID, even though it is valid. He's looking into it.
    # {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Conjure:UnprocessableEntity', 'errorInstanceId': 'c3eefa5a-61b9-45fc-aaa7-30355c15c92b', 'parameters': {}}
    # temporarily passed in no id to see if it works and it did. Will wait for the updated api 2/2/2022
    cs_version_expression_dict = code_set_expression_items_json_all_rows = [0]
    response_json = post_request_enclave_api(api_url, header, json.dumps(cs_version_expression_dict))

    # TODO: After successful validations, do real POSTs (check if they exist first)?

    return response_json

if __name__ == '__main__':
    run(None)
