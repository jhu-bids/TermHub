"""Main module
# TODO:
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
import json
import pandas as pd
from enclave_wrangler.config import PROJECT_ROOT, config
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
VSAC_LABEL_PREFIX = '[VSAC] '
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

    # Read data
    code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    if 'codeset_id' not in code_sets_df.columns:
        print('WTF???')
    # For some reason, was being read with .0's at the end.
    code_sets_df['enclave_codeset_id'] = pd.to_numeric(code_sets_df['enclave_codeset_id'], errors='coerce')\
        .astype('Int64')
    # be sure to strip the spaces in the beginning and the end of the name
    code_sets_df.columns.str.lstrip()
    code_sets_df.columns.str.rstrip()

    # 0.1 Create mappings between
    # - concept_set_container_edited.csv[concept_set_name], and...
    # - code_sets.csv[codeset_id]
    # use the concept_set_name as key to store the pre-made codeset_ids,
    # store the codeset_ids in the premade_codeset_ids
    cs_name_id_mappings = {}
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

    # I.3. Build all of the Expression items to add to a CS version; key=codeset_id,
    # codeset_id = pre-made codeset_id to iterate through the codesets
    code_set_expression_items_json_all_rows = {}
    for index, row in code_sets_df.iterrows():
        current_code_set_id = row['codeset_id']
        # build the code and codeSystem list for the current codeSet
        # reset the code list
        code_list = []
        cs_name = row['concept_set_name']
        # code and code system list
        concept_set_version_item_rows = concept_set_version_item_dict[current_code_set_id]
        # always use the same entry from the first set as currently
        # we do not have a support to save these flags per expressionItems
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


    # --- Steph: check the failed cases 2/15/22-----------------------------
    # @Steph: Can we remove this block yet? I don't mind keeping for a while for convenienice, but I like the practice
    # ...of keeping code like this inside a copy of the file in a git ignored folder. - Joe 2022/03/15
    # begin test code
    # for premade_codeset_id in premade_codeset_ids:
    #    # we have problem with very large code list - 16(3623) and 39(5104) 58(1820) 73(6791) 74(1501)
    #    upd_cs_ver_expression_items_dict1 = code_set_expression_items_json_all_rows[premade_codeset_id]
    #    codeStringList1 = upd_cs_ver_expression_items_dict1['parameters']['ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33']['stringList']['strings']
    #    print( str(premade_codeset_id) + "codelistLength: " + str(len(codeStringList1)))
    #    print('------')
    # end test code ------------------------------- #


    # II. call the REST APIs to create them on the Enclave
    # ...now that we have all the data from concept set are created
    temp_testing_cset_id = 1000000326  # Stephanie said this was a draft or archived set - Joe 2022/03/15
    for premade_codeset_id in premade_codeset_ids:
        # TODO: temporary debug code to look for missing concept container not showing in the UI
        # TODO: debug code for adding expressionItems to missing container from UI, l162,l163
    #    if premade_codeset_id != temp_testing_cset_id:
    #        continue

        # Do a test first using 'validate'
        header = {
                "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
                'content-type': 'application/json'
        }

        container_data_dict = concept_set_container_edited_json_all_rows[premade_codeset_id]
        # noinspection PyUnusedLocal
        # response_json = post_request_enclave_api(api_url, header, test_data_dict)
        # create concept set container -----container_data_dict['parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']
        # 'ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807': {'type': 'string', 'string': '[VSAC] Eclampsia'},
        #if DEBUG:
            #csContainerName = container_data_dict['parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']['string']
            #print(csContainerName)
            #print('------------------------------')
        response_json = post_request_enclave_api_create_container(header, container_data_dict)
        # i.e container object may already exist but we can create another version within a container: {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Actions:ObjectsAlreadyExist', 'errorInstanceId': '96fb2188-1947-4004-a7b3-d0572a5a0008', 'parameters': {'objectLocators': '[ObjectLocator{objectTypeId: omop-concept-set-container, primaryKey: {concept_set_id=PrimaryKeyValue{value: StringWrapper{value: [VSAC] Mental Behavioral and Neurodevelopmental Disorders}}}}]'}}
        # Validate 2: Concept set version item
        # noinspection PyUnusedLocal
        # DEBUG:urllib3.connectionpool:https://unite.nih.gov:443 "POST /actions/api/actions HTTP/1.1" 200 107
        # {'actionRid': 'ri.actions.main.action.9dea4a02-fb9c-4009-b623-b91ad6a0192b', 'synchronouslyPropagated': False}
        # Actually create a version so that we can test the api to add the expression items

        # cs_version_data_dict = code_set_version_json_all_rows[0]
        cs_version_data_dict = code_set_version_json_all_rows[premade_codeset_id]
        # noinspection PyUnusedLocal
        # create the version and ask Enclave for the codeset_id that can be used to addCodeExpressionItems
        # create version -----
        codeset_id = post_request_enclave_api_create_version(header, cs_version_data_dict)
        # TODO begin ------------------------------------------------------------
        # 3/14/22, stephanie, save the codeset_id with container name in csContainerName
        # save codeset_id of a draft version with the container name saved in container_name= container_data_dict['parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']['string']
        # premade_codeset_id = dih internal id
        # csContainerName = container name
        # codeset_id = version id
        # --persist the data in the output folder = input_csv_folder_path
        # end TODO---------------------------------------------------------------
        # upd_cs_ver_expression_items_dict = code_set_expression_items_json_all_rows[item]
        upd_cs_ver_expression_items_dict = code_set_expression_items_json_all_rows[premade_codeset_id]
        # update the payload with the codeset_id returned from the

        # DEBUG: Can use this to check to make sure code list is OK:
        # if DEBUG: # updated json data is saved in upd_cs_ver_expression_items_dict
        csContainerName = \
        container_data_dict['parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807'][
            'string']
        print('csContainerName: ' + str(csContainerName))
        stringList = upd_cs_ver_expression_items_dict['parameters']['ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33']['stringList']['strings']
        print('premade_codeset_id: ' + str(premade_codeset_id))
        print('len(stringList): ' + str(len(stringList)))
        print('codeset_id: ' + str(codeset_id))
        print('------------------------------')

        # update the json data with the correct codeset_id -----
        upd_cs_ver_expression_items_dict = \
            update_cs_version_expression_data_with_codesetid(codeset_id, upd_cs_ver_expression_items_dict)


        # Validate 3: add the concept set expressions to draft version by passing as code and code system
        # third api
        # https://unite.nih.gov/workspace/ontology/action-type/add-code-system-codes-as-omop-version-expressions/overview
        # action type rid: ri.actions.main.action-type.e07f2503-c7c9-47b9-9418-225544b56b71
        # noinspection PyUnusedLocal
        # add expressionItems to version -----
        response_json = post_request_enclave_api_addExpressionItems(header, upd_cs_ver_expression_items_dict)
        print('post request to add expressionItems returned: ----------' + json.dumps(response_json))
        # Once the expression items has been added save the enclave concept_id so that we can update the code_sets.csv file
        # update code_sets_df with the enclave_codeset_id column of the  value in the codeset_id retured from the enclave
        # and if needed we can also save the json data in upd_cs_ver_expression_items_dict
        # premade_codeset_id is stored in the codeset_id column in the csv files, save the id in the enclave_codeset_id column
        # update when it was uploaded as well, Stephane 3/15/22
        try:
            code_sets_df.set_index('codeset_id', inplace=True)
        except Exception as e:
            print(e)

        code_sets_df.at[premade_codeset_id, 'enclave_codeset_id'] = codeset_id
        code_sets_df.at[premade_codeset_id, 'enclave_codeset_id_updated_at'] = _datetime_palantir_format()
        code_sets_df = code_sets_df.reset_index()
        # return response_json


    # write out the update csv file with the enclave_codeset_id
    # print('before terminating write out the updated code_sets.csv file here')
    # date_str = datetime.now().strftime('%Y_%m_%d_%H_%M')
    # output_filename = 'code_sets_updated_' + date_str + '.csv'
    output_filename = 'code_sets.csv'
    code_sets_df.to_csv(os.path.join(input_csv_folder_path, output_filename), index=True, encoding='utf-8')

    # Save to persistence layer
    persistence_csv_path = os.path.join(PROJECT_ROOT, 'data', 'cset.csv')
    code_sets_df_limited = code_sets_df[['codeset_id', 'enclave_codeset_id', 'enclave_codeset_id_updated_at', 'concept_set_name']]
    persistence_df = pd.read_csv(persistence_csv_path).fillna('')
    persistence_df_new = persistence_df.merge(
        code_sets_df_limited, how='left', left_on='internal_id', right_on='codeset_id').fillna('')
    persistence_df_new.to_csv(persistence_csv_path, index=False)

if __name__ == '__main__':
    run(None)
