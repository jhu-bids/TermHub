"""Main module
# TODO's:
- For mappings, I believe Amin will be providing us to .parquet files. We can read with pandas:
--https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html

Resources
- Validate URL (for testing POSTs without it actually taking effect): https://unite.nih.gov/actions/api/actions/validate
# TODO: Update wiki article to be up-to-date with correct params for 'concept set version':
- Wiki article on how to create these JSON:
- https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs
  - CreateNewDraftOMOPConceptSetVersion: code_sets.csv
  - CreateNewConceptSet: concept_set_container_edited.csv
  - addCodeAsVersionExpression: concept_set_version_item_rv_edited.csv
"""
import os
from datetime import datetime, timezone

import pandas as pd
from enclave_wrangler.config import config
from enclave_wrangler.enclave_api import get_cs_container_data
from enclave_wrangler.enclave_api import get_cs_version_data
from enclave_wrangler.enclave_api import get_cs_version_expression_data
from enclave_wrangler.enclave_api import post_request_enclave_api_addExpressionItems
from enclave_wrangler.enclave_api import post_request_enclave_api_create_container
from enclave_wrangler.enclave_api import post_request_enclave_api_create_version
from enclave_wrangler.enclave_api import update_cs_version_expression_data_with_codesetid
from enclave_wrangler.utils import log_debug_info


# TODO: Add debug as a CLI param
DEBUG = False
# PALANTIR_ENCLAVE_USER_ID_1: This is an actual ID to a valid user in palantir, who works on our BIDS team.
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
VSAC_LABEL_PREFIX = '[VSAC Bulk-Import test1] '
# API_URL query params:
# 1. ?synchronousPropagation=false: Not sure what this does or if it helps.
API_CREATE_URL = 'https://unite.nih.gov/actions/api/actions'
# Based on curl usage, it seems that '?synchronousPropagation=false' is not required
# API_VALIDATE_URL = 'https://unite.nih.gov/actions/api/actions/validate'
API_VALIDATE_URL = 'https://unite.nih.gov/actions/api/actions/validate?synchronousPropagation=false'


def _datetime_palantir_format() -> str:
    """Returns datetime str in format used by palantir data enclave
    e.g. 2021-03-03T13:24:48.000Z (milliseconds allowed, but not common in observed table)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'


def run(input_csv_folder_path):
    """Main function"""
    if DEBUG:
        log_debug_info()

    # 0.1 Create mappings between
    # - concept_set_container_edited.csv[concept_set_name], and...
    # - code_sets.csv[codeset_id]
    cs_name_id_mappings = {}
    code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    for index, row in code_sets_df.iterrows():
        cs_id = row['codeset_id']
        cs_name = row['concept_set_name']
        cs_name_id_mappings[cs_name] = cs_id
    # 0.2 create a list of premade coedeset ids
    premade_codeset_ids = []
    for index, row in code_sets_df.iterrows():
        premade_codeset_ids.append(row['codeset_id'])

    # I. Create structures
    # I.0. concept_set_version_item_dict; key=codeset_id
    concept_set_version_item_dict = {}
    concept_set_version_item_rv_edited_df = pd.read_csv(
        os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')
    for index, row in concept_set_version_item_rv_edited_df.iterrows():
        key = row['codeset_id']
        if key not in concept_set_version_item_dict:
            concept_set_version_item_dict[key] = []
        concept_set_version_item_dict[key].append(row)
    # cs_result = pd.merge(code_sets_df, concept_set_version_item_rv_edited_df, on=['codeset_id'])

    # I.1. build the list of container json data; key=codeset_id
    # I.1.ii. Get the actual container data
    concept_set_container_edited_json_all_rows = {}
    concept_set_container_edited_df = pd.read_csv(
        os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    for index, row in concept_set_container_edited_df.iterrows():
        cs_name = row['concept_set_name']
        single_row = get_cs_container_data(cs_name)
        cs_id = cs_name_id_mappings[cs_name]
        concept_set_container_edited_json_all_rows[cs_id] = single_row

    # I.2. build the list of cs version json data; key=codeset_id
    code_set_version_json_all_rows = {}
    # code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    for index, row in code_sets_df.iterrows():
        cs_id = row['codeset_id']
        cs_name = row['concept_set_name']
        cs_intention = row['intention']
        cs_limitations = row['limitations']
        cs_update_msg = row['update_message']
        # cs_status = row['status']
        cs_provenance = row['provenance']
        single_row = get_cs_version_data(cs_name, cs_id, cs_intention, cs_limitations, cs_update_msg, cs_provenance)
        # cs_name, cs_id, intension, limitation, update_msg, status, provenance
        code_set_version_json_all_rows[cs_id] = single_row
        # code_set_version_json_all_rows_dict[codeset_id] = single_row

    # I.3. Expression items; key=codeset_id
    code_set_expression_items_json_all_rows = {}
    for index, row in code_sets_df.iterrows():
        current_code_set_id = row['codeset_id']
        # build the code and codeSystem list for the current codeSet
        # reset the code list
        code_list = []
        cs_name = row['concept_set_name']
        # code and code system list
        concept_set_version_item_rows = concept_set_version_item_dict[current_code_set_id]
        concept_set_version_item_row1 = concept_set_version_item_rows[0]
        exclude = concept_set_version_item_row1['isExcluded']
        descendents = concept_set_version_item_row1['includeDescendants']
        mapped = concept_set_version_item_row1['includeMapped']
        annotation = concept_set_version_item_row1['annotation']

        for concept_set_version_item_row in concept_set_version_item_rows:
                code_codesystem_pair = concept_set_version_item_row['codeSystem'] + ":" + concept_set_version_item_row['code']
                code_list.append(code_codesystem_pair)
                # to-do(future): Right now, the API doesn't expect variation between the following 4 values among
                # ...concept set items, so right now we can just take any of the rows and use its values. But, in
                # ...the future, when there is variation, we may need to do some update here. - Joe 2022/02/04
                # this is same limitation OMOP concept expression works, so for now it is sufficient
                # we can explorer more granular control later if necessary -Stephanie 02/05/2022

                # now that we have the code list, generate the json for the versionExpression data
                single_row = get_cs_version_expression_data(
                    current_code_set_id, cs_name, code_list, exclude, descendents, mapped, annotation)
                code_set_expression_items_json_all_rows[current_code_set_id] = single_row
                # code_set_expression_items_json_all_rows_dict[codeset_id] = single_row

    # II. call the REST APIs to create them on the Enclave
    # ...now that we have all the data from concept set are created
    for premade_codeset_id in premade_codeset_ids:
        # Do a test first using 'valdiate'
        api_url = API_VALIDATE_URL
        header = {
            "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
            'content-type': 'application/json'
        }

        test_data_dict = concept_set_container_edited_json_all_rows[premade_codeset_id]
        # noinspection PyUnusedLocal
        #response_json = post_request_enclave_api(api_url, header, test_data_dict)
        response_json = post_request_enclave_api_create_container(api_url, header, test_data_dict)

        # Validate 2: Concept set version item
        # noinspection PyUnusedLocal
        # DEBUG:urllib3.connectionpool:https://unite.nih.gov:443 "POST /actions/api/actions HTTP/1.1" 200 107
        # {'actionRid': 'ri.actions.main.action.9dea4a02-fb9c-4009-b623-b91ad6a0192b', 'synchronouslyPropagated': False}
        # Actually create a version so that we can test the api to add the expression items

        # cs_version_data_dict = code_set_version_json_all_rows[0]
        cs_version_data_dict = code_set_version_json_all_rows[premade_codeset_id]
        # noinspection PyUnusedLocal
        # create the version and ask Enclave for the codeset_id that can be used to addCodeExpressionItems
        codeset_id = post_request_enclave_api_create_version(header, cs_version_data_dict)
        # upd_cs_ver_expression_items_dict = code_set_expression_items_json_all_rows[item]
        upd_cs_ver_expression_items_dict = code_set_expression_items_json_all_rows[premade_codeset_id]
        # update the payload with the codeset_id returned from the

        # DEBUG: Can use this to check to make sure code list is OK:
        # stringList = upd_cs_ver_expression_items_dict['parameters']['ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33']['stringList']['strings']
        # print(premade_codeset_id)
        # print(len(stringList))
        # print('---')

        upd_cs_ver_expression_items_dict = \
            update_cs_version_expression_data_with_codesetid(codeset_id, upd_cs_ver_expression_items_dict)


        # Validate 3: add the concept set expressions to draft version by passing as code and code system
        # third api
        # https://unite.nih.gov/workspace/ontology/action-type/add-code-system-codes-as-omop-version-expressions/overview
        # action type rid: ri.actions.main.action-type.e07f2503-c7c9-47b9-9418-225544b56b71
        # noinspection PyUnusedLocal
        response_json = post_request_enclave_api_addExpressionItems(header, upd_cs_ver_expression_items_dict)
        # print(json.dumps(response_json))
        # return response_json


if __name__ == '__main__':
    run(None)
