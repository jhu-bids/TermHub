"""Upload datasets to Foundry"""
import json
import os
from argparse import ArgumentParser
from random import randint
from typing import Dict, List, Set, Union
from uuid import uuid4
from time import sleep

import pandas as pd
from requests import Response

# TODO: See if sys.path(0) thing works; doesn't require maintenance. Look at unit tests
try:
    from enclave_wrangler.config import CSET_UPLOAD_REGISTRY_PATH, CSET_VERSION_MIN_ID, ENCLAVE_PROJECT_NAME, MOFFIT_PREFIX, \
    MOFFIT_SOURCE_ID_TYPE, MOFFIT_SOURCE_URL, PALANTIR_ENCLAVE_USER_ID_1, UPLOADS_DIR, VALIDATE_FIRST, config, \
    PROJECT_ROOT, \
    TERMHUB_CSETS_DIR
    from enclave_wrangler.actions_old_palantir3file_api import get_cs_container_data, get_cs_version_data, get_cs_version_expression_data, \
    post_request_enclave_api_addExpressionItems, post_request_enclave_api_create_container, \
    post_request_enclave_api_create_version, update_cs_version_expression_data_with_codesetid
    from enclave_wrangler.actions_api import add_concepts_to_cset, finalize_concept_set_version, \
    upload_concept_set_container, \
    upload_concept_set_version, get_concept_set_version_expression_items
    from enclave_wrangler.utils import EnclaveWranglerErr, _datetime_palantir_format, log_debug_info, make_actions_request
except ModuleNotFoundError:
    from config import CSET_UPLOAD_REGISTRY_PATH, ENCLAVE_PROJECT_NAME, MOFFIT_PREFIX, \
    MOFFIT_SOURCE_ID_TYPE, MOFFIT_SOURCE_URL, PALANTIR_ENCLAVE_USER_ID_1, UPLOADS_DIR, config, PROJECT_ROOT, \
    TERMHUB_CSETS_DIR, CSET_VERSION_MIN_ID
    from actions_old_palantir3file_api import get_cs_container_data, get_cs_version_data, get_cs_version_expression_data, \
        post_request_enclave_api_addExpressionItems, post_request_enclave_api_create_container, \
        post_request_enclave_api_create_version, update_cs_version_expression_data_with_codesetid
    from actions_api import add_concepts_to_cset, upload_concept_set_container, \
        upload_concept_set_version, get_concept_set_version_expression_items
    from utils import _datetime_palantir_format, log_debug_info


DEBUG = False

# TODO: return 'outcome': success / error for (i) all the csets, (ii) each cset baesd on all response.status_code
def upload_new_cset_version_with_concepts_from_csv(
    path: str = None, df: pd.DataFrame = None, validate_first=False
) -> Dict:
    """
    Upload from CSV
    file format docs:
    https://github.com/jhu-bids/TermHub/tree/develop/enclave_wrangler

    testing from test/test_enclave_wrangler.py
    using:
    https://github.com/jhu-bids/TermHub/blob/develop/test/input/test_enclave_wrangler/test_dataset_upload/type-2-diabetes-mellitus.csv

    :return A dictionary of wth cset name as key, and values are the responses from each enclave API call to fulfill
    the request.
    """
    if not path and df is None:
        raise RuntimeError('upload_new_cset_version_with_concepts_from_csv: Must provide path or dataframe')
    df = df if df is not None else pd.read_csv(path).fillna('')
    df = df[~df.eq('').all(axis=1)]  # drop all empty rows

    cset_group_cols = ['concept_set_name', 'parent_version_codeset_id']
    more_cset_cols = list(
        {'multipassId', 'current_max_version', 'domain_team', 'provenance', 'limitations', 'intention',
         'intended_research_project', 'authority'}.intersection(df.columns))
    concept_cols_required = ['concept_id', 'includeDescendants', 'isExcluded', 'includeMapped']
    concept_cols_optional = ['annotation']

    responses = {}
    csets = df.groupby(cset_group_cols)
    for cset in csets:
        key: tuple
        key, csetdf = cset

        new_version = {}
        cset_name = key[0]
        new_version['concept_set_name'] = cset_name
        new_version['parent_version_codeset_id'] = int(key[1])

        first_row = csetdf[more_cset_cols].to_dict(orient='records')[0]
        for c in more_cset_cols:
            new_version[c] = first_row[c]

        new_version['on_behalf_of'] = new_version['multipassId']
        del new_version['multipassId']

        selectable_cols = concept_cols_required + [x for x in concept_cols_optional if x in list(csetdf.columns)]
        try:
            new_version['omop_concepts'] = csetdf[selectable_cols].to_dict(orient='records')
        except KeyError as e:
            raise EnclaveWranglerErr(str(e))
        for x in new_version['omop_concepts']:
            x['concept_id'] = int(x['concept_id'])

        # TODO: for now going to assume that if the concept set exists, they'll give us a parent_version_codeset_id
        #   but they might give us the name and not the parent id. if they do give us the name but the
        #   name already exists, two possibilities: 1) they just want to add a new version using the most
        #   recent version as the parent but didn't bother to find out what it was and include in csv, or
        #   2) it's a mistaken duplicate name and they should get an error and have to change the name
        #   FIX SOMEHOW!!!

        if new_version['parent_version_codeset_id']:   # creating new version, setting parent to existing version
            responses_i: Dict = upload_new_cset_version_with_concepts(**new_version, validate_first=validate_first)
            # TODO: since test/test_enclave_wrangler.py:test_upload() is only expecting one
            #   result, just returning the first result. but csvs allow multiple, so FIX THIS!!!!
        else:
            responses_i: Dict = upload_new_container_with_concepts(**new_version, validate_first=validate_first)
        responses[cset_name] = responses_i

        # TODO: put something helpful back here but that doesn't cause errors
        # print('INFO: ' + cset_name + ': ', str(responses_i))
        print('INFO: ' + cset_name)
    return responses


# TODO
def upload_new_cset_container_with_concepts_from_csv(
    path: str = None, df: pd.DataFrame = None, validate_first=False
) -> Dict:
    """Upload new container from CSV"""
    if not path and df is None:
        raise RuntimeError('upload_new_cset_version_with_concepts_from_csv: Must provide path or dataframe')
    df = df if df is not None else pd.read_csv(path).fillna('')
    # response = upload_new_container_with_concepts(
    #     container=d.container,
    #     versions_with_concepts=d.versions_with_concepts)
    return {}


# TODO: What if this fails halfway through? Can we teardown any of the steps? (need to store random `codeset_id` too)
# TODO: Need to do proper codeset_id assignment: (i) look up registry and get next available ID, (ii) assign it here,
#  (iii) persist new ID / set to registry, (iv) persist new ID to any files passed through CLI, (v), return the new ID
# todo: @Siggie: Do we want to change this to accept named params instead of a dictionary? - Joe 2022/12/05
def upload_new_cset_version_with_concepts(
    concept_set_name: str, parent_version_codeset_id: int, current_max_version: float, omop_concepts: List[Dict],
    provenance: str = "", limitations: str = "", intention: str = "", annotation: str = "",
    intended_research_project: str = None, on_behalf_of: str = None, codeset_id: int = None,
    validate_first=VALIDATE_FIRST
) -> Dict:
    """Upload a concept set version along with its concepts.

    # todo: Update this slightly now that this function accepts named params instead of a dict 
    
        'omop_concepts': [
          {
            'concept_id' (int) (required):
            'includeDescendants' (bool) (required):
            'isExcluded' (bool) (required):
            'includeMapped' (bool) (required):
            'annotation' (str) (optional):
          }
        ],
        'provenance' (str) (required):
        'concept_set_name' (str) (required):
        'limitations' (str) (required):
        'intention' (str) (required):
        'annotation' (str) (optional): Default:`'Curated value set: ' + version['concept_set_name']`
        'intended_research_project' (str) (optional): Default:`ENCLAVE_PROJECT_NAME`
        'codeset_id' (int) (required): Default:Will ge generated if not passed.
    }

    Example:
    {
        "omop_concepts": [
            {
              "concept_id": 45259000,
              "includeDescendants": true,
              "isExcluded": false,
              "includeMapped": true,
              "annotation": "This is my concept annotation."
            }
        ],
        "provenance": "Created through TermHub.",
        "concept_set_name": "My test concept set",
        "limitations": "",
        "intention": ""
    }
    """
    # Handle missing params
    if not codeset_id:
        # todo: this is temporary until I handle registry persistence
        arbitrary_range = 100000
        codeset_id = randint(CSET_VERSION_MIN_ID, CSET_VERSION_MIN_ID + arbitrary_range)
    if not intended_research_project:
        intended_research_project = ENCLAVE_PROJECT_NAME

    # Upload
    response_upload_draft_concept_set: Response = upload_concept_set_version(  # code_set
        base_version=parent_version_codeset_id,
        current_max_version=current_max_version,
        provenance=provenance,
        concept_set=concept_set_name,  # == container_d['concept_set_name']
        annotation=annotation,
        limitations=limitations,
        intention=intention,
        intended_research_project=intended_research_project,
        version_id=codeset_id,
        on_behalf_of=on_behalf_of,
        validate_first=validate_first)  # == code_sets.codeset_id
    sleep(8)

    response_upload_concepts: List[Response] = add_concepts_to_cset(
        omop_concepts=omop_concepts,
        version__codeset_id=codeset_id,
        validate_first=validate_first)  # == code_sets.codeset_id

    response_finalize_concept_set_version: Response = finalize_concept_set_version(
        concept_set=concept_set_name,  # == container_d['concept_set_name']
        version_id=codeset_id,
        current_max_version=current_max_version,
        provenance=provenance,
        limitations=limitations,
        validate_first=validate_first)

    return {
        'responses': {
            'upload_concept_set_version': response_upload_draft_concept_set,
            'add_concepts_to_cset': response_upload_concepts,
            'finalize_concept_set_version': response_finalize_concept_set_version
        },
        'versionId': codeset_id
    }



# TODO: support concept params, e.g. exclude_children
def upload_new_container_with_concepts(
    container: Dict, versions_with_concepts: List[Dict], validate_first=VALIDATE_FIRST
) -> Dict:
    """Upload a new concept set container, and 1+ concept set versions, along with their concepts.

    :param container (Dict): Has the following keys:
        concept_set_name (str) (required):
        intention (str) (required):
        research_project (str) (required): Default:`ENCLAVE_PROJECT_NAME`
        assigned_sme (str) (optional): Default:`PALANTIR_ENCLAVE_USER_ID_1`
        assigned_informatician (str) (optional): Default:`PALANTIR_ENCLAVE_USER_ID_1`
    :param versions_with_concepts (List[Dict]): Has the following schema: [
      {
        'version': {
          'omop_concept_ids': (List[int]) (required),

          'provenance' (str) (required):
          'concept_set_name' (str) (required):
          'annotation' (str) (optional): Default:`'Curated value set: ' + version['concept_set_name']`
          'limitations' (str) (required):
          'intention' (str) (required):
          'intended_research_project' (str) (optional): Default:`ENCLAVE_PROJECT_NAME`
          'codeset_id' (int) (required):
        }
      }
    ]
    """
    response_upload_concept_set: Response = upload_concept_set_container(  # concept_set_container
        concept_set_id=container['concept_set_name'],
        intention=container['intention'],
        research_project=container.get('research_project', ENCLAVE_PROJECT_NAME),
        assigned_sme=container.get('assigned_sme', PALANTIR_ENCLAVE_USER_ID_1),
        assigned_informatician=container.get('assigned_informatician', PALANTIR_ENCLAVE_USER_ID_1),
        validate_first=validate_first)

    response_upload_new_cset_version_with_concepts = []
    for version in versions_with_concepts:
        response_versions_i: Dict[str, Union[Response, List[Response]]] = \
            upload_new_cset_version_with_concepts(**version, validate_first=validate_first)
        response_upload_new_cset_version_with_concepts.append(response_versions_i)

    return {
        'upload_concept_set_container': response_upload_concept_set,
        'upload_new_cset_version_with_concepts': response_upload_new_cset_version_with_concepts}



# todo: need to have 2 variations: 1 for creates, and 1 for updates. w/ exception handling and proper error messaging
# todo: need to allow 'upload' based on if it is / isn't in the local termhub-csets/datasets/cset_upload_registry.csv
# todo: use CSET_VERSION_MIN_ID? right now I'm not sure. makes more sense to pre-assign before running this so that
#  ...I can JOIN together. would need a separate function just to accept a single `linked_cset` as opposed to files
#  ...that have multiple. otherwise, with multiple, there's no way to tell what concepts for what cset
def post_to_enclave_from_3csv(
    input_csv_folder_path: str, enclave_api=['old_rid_based', 'default'][1], create_cset_container=True,
    create_cset_versions=True
) -> Union[Dict, pd.DataFrame]:
    """Uploads data to enclave and updates the following column in the input's code_sets.csv:
    # todo: Siggie: updating these files is probably not worth / necessary right now. Joe: We might want to do at some point
    - enclave_codeset_id
    - enclave_codeset_id_updated_at
    - concept_set_name

    :param enclave_api (str): One of 'old_rid_based' or 'default'. The 'old_rid_based' Enclave API is the one which
    required RIDs for params rather than the param name, and there may be other differences. 'default' refers to the
    newer Enclave API (as of 2022/10).

    # todo: after adding 'update' functionality, add params / update these docs
    :param create_cset_container (bool): If true, will identify concept set containers from `input_csv_folder_path` and
    make a POST request to enclave to create them. Only applicable to the new 'default' API.
    :param create_cset_versions (bool): If true, will identify concept set versions from `input_csv_folder_path` and
    make a POST request to enclave to create them. Only applicable to the new 'default' API.
    """
    # Settings
    if DEBUG:
        log_debug_info()
    # Validate
    msg = 'post_to_enclave_from_3csv() has not yet been set up to only add ' \
          'concepts. Must either pass `create_cset_container=True` to create ' \
          'a new concept set container, `create_cset_versions=True` to create' \
          ' new concept set versions on an existing container, or both.' \
          ' Doing nothing.'
    if not create_cset_container or create_cset_versions:
        print(msg)
        return {}
    # Routing
    if enclave_api == 'old_rid_based':
        # todo: this doesn't return Response, so might want to change this functions return sig / val
        df: pd.DataFrame = post_to_enclave_old_api(input_csv_folder_path)
        return df

    # Read data
    concept_set_container_edited_df = pd.read_csv(
        os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    concept_set_container_edited_d = json.loads(concept_set_container_edited_df.to_json(orient='records'))
    code_sets_df = _load_standardized_input_df(os.path.join(input_csv_folder_path, 'code_sets.csv'))  # .fillna('')
    concept_set_version_item_rv_edited_df = pd.read_csv(
        os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')

    # Link data into single iterable
    # temp: @Siggie: You mentioned to delete the internal_id we assigned, but I don't know how to link these together otherwise
    linked_csets: Dict = {}
    for container_d in concept_set_container_edited_d:
        cset_name = container_d['concept_set_id']
        linked_csets[cset_name] = {'versions': {}}
        linked_csets[cset_name]['container'] = container_d
        code_sets_df_i = code_sets_df[code_sets_df['concept_set_name'] == cset_name]
        code_sets_d_i = json.loads(code_sets_df_i.to_json(orient='records'))
        for version_d in code_sets_d_i:
            version_id = version_d['codeset_id']  # == code_sets.codeset_id
            linked_csets[cset_name]['versions'][version_id] = {'items': []}
            linked_csets[cset_name]['versions'][version_id]['version'] = version_d
            concept_set_version_item_rv_edited_df_i = concept_set_version_item_rv_edited_df[
                concept_set_version_item_rv_edited_df['codeset_id'] == version_id]  # == code_sets.codeset_id
            concept_set_version_item_rv_edited_d_i = json.loads(concept_set_version_item_rv_edited_df_i.to_json(orient='records'))
            for item_d in concept_set_version_item_rv_edited_d_i:
                linked_csets[cset_name]['versions'][version_id]['omop_concept_ids'].append(item_d)

    # Upload to enclave
    response_upload_new_container_with_concepts = {}
    response_upload_concept_set: Union[None, Response] = None
    response_upload_new_cset_version_with_concepts = {}
    for linked_cset in list(linked_csets.values()):
        container_d = linked_cset['container']
        if create_cset_container and create_cset_versions:
            response_upload_new_container_with_concepts: Dict = upload_new_container_with_concepts(
                container=container_d,
                versions_with_concepts=linked_cset['versions'].values())
        elif create_cset_container:
            response_upload_concept_set: Response = upload_concept_set_container(  # concept_set_container
                concept_set_id=container_d['concept_set_name'],
                intention=container_d['intention'],
                research_project=ENCLAVE_PROJECT_NAME,
                assigned_sme=PALANTIR_ENCLAVE_USER_ID_1,
                assigned_informatician=PALANTIR_ENCLAVE_USER_ID_1)
        elif create_cset_versions:
            response_upload_new_cset_version_with_concepts = []
            for version in linked_cset['versions'].values():
                version_d = version['version']
                version_d['omop_concept_ids'] = version['omop_concept_ids']
                response_i: Dict[str, Union[Response, List[Response]]] = upload_new_cset_version_with_concepts(**version_d)
                response_upload_new_cset_version_with_concepts.append(response_i)

    return {
        'upload_new_container_with_concepts': response_upload_new_container_with_concepts,
        'upload_concept_set': response_upload_concept_set,
        'upload_new_cset_version_with_concepts': response_upload_new_cset_version_with_concepts}


def post_to_enclave_old_api(input_csv_folder_path: str) -> pd.DataFrame:
    """Uploads data to enclave and updates the following column in the input's code_sets.csv:
    - enclave_codeset_id
    - enclave_codeset_id_updated_at
    - concept_set_name
    """
    if DEBUG:
        log_debug_info()

    # Read data
    code_sets_df = _load_standardized_input_df(os.path.join(input_csv_folder_path, 'code_sets.csv')) #.fillna('')

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
        cs_name = row['concept_set_name'].strip()
        single_row = get_cs_container_data(cs_name)
        cs_id = cs_name_id_mappings[cs_name]
        concept_set_container_edited_json_all_rows[cs_id] = single_row

    # I.2. build the list of cs version json data; key=codeset_id
    code_set_version_json_all_rows = {}
    # code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    for index, row in code_sets_df.iterrows():
        cs_id = row['codeset_id']
        cs_name = row['concept_set_name'].strip()
        cs_intention = row['intention'].strip()
        cs_limitations = row['limitations'].strip()
        cs_update_msg = row['update_message'].strip()
        cs_authority = row.get('authority', '').strip()
        ##cs_authority = "Mathematica"  ## TODO: shong, 4/26/22, code_sets.csv need to build the authority value, uncomment when available
        cs_provenance = row['provenance'].strip()
        single_row = get_cs_version_data(cs_name, cs_id, cs_intention, cs_limitations, cs_update_msg, cs_provenance, cs_authority)
        # cs_name, cs_id, intention, limitation, update_msg, status, provenance
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
        cs_name = row['concept_set_name'].strip()
        # code and code system list
        concept_set_version_item_rows = concept_set_version_item_dict[current_code_set_id]
        # always use the same entry from the first set as currently
        # we do not have a support to save these flags per expressionItems
        concept_set_version_item_row1 = concept_set_version_item_rows[0]
        exclude = concept_set_version_item_row1['isExcluded']
        descendents = concept_set_version_item_row1['includeDescendants']
        mapped = concept_set_version_item_row1['includeMapped']
        annotation = concept_set_version_item_row1['annotation'].strip()

        for concept_set_version_item_row in concept_set_version_item_rows:
            code_codesystem_pair = concept_set_version_item_row['codeSystem'] + ":" + str(concept_set_version_item_row['code'])
            code_list.append(code_codesystem_pair)
            # to-do(future): Right now, the API doesn't expect variation between the following 4 values among
            # ...concept set items, so right now we can just take any of the rows and use its values. But, in
            # ...the future, when there is variation, we may need to do some update here. - Joe 2022/02/04
            # this is same limitation OMOP concept expression works, so for now it is sufficient
            # we can explorer more granular control later if necessary -Stephanie 02/05/2022

            # now that we have the code list, generate the json for the versionExpression data
            single_row = get_cs_version_expression_data(current_code_set_id, cs_name, code_list, exclude, descendents, mapped, annotation)
            code_set_expression_items_json_all_rows[current_code_set_id] = single_row
            # code_set_expression_items_json_all_rows_dict[codeset_id] = single_row

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
    #    codeStringList1 = upd_cs_ver_expression_items_dict1['parameters'][
    #        'ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33']['stringList']['strings']
    #    print( str(premade_codeset_id) + "codelistLength: " + str(len(codeStringList1)))
    #    print('------')
    # end test code ------------------------------- #

    # II. call the REST APIs to create them on the Enclave
    # ...now that we have all the data from concept set are created
    # temp_testing_cset_id = 1000000326  # Stephanie said this was a draft or archived set - Joe 2022/03/15
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
        # create concept set containe:
        #  ----- container_data_dict['parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']
        # 'ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807': {
        #   'type': 'string', 'string': '[VSAC] Eclampsia'},
        # if DEBUG:
        #     csContainerName = container_data_dict[
        #         'parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']['string']
        #     print(csContainerName)
        #     print('------------------------------')
        response_json = post_request_enclave_api_create_container(header, container_data_dict)
        # i.e container object may already exist but we can create another version within a container:
        # {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Actions:ObjectsAlreadyExist',
        # 'errorInstanceId': '96fb2188-1947-4004-a7b3-d0572a5a0008', 'parameters': {'objectLocators':
        # '[ObjectLocator{objectTypeId: omop-concept-set-container, primaryKey: {concept_set_id=PrimaryKeyValue{
        #   value: StringWrapper{value: [VSAC] Mental Behavioral and Neurodevelopmental Disorders}}}}]'}}
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
        # save codeset_id of a draft version with the container name saved in container_name= container_data_dict[
        #   'parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']['string']
        # premade_codeset_id = dih internal id
        # csContainerName = container name
        # codeset_id = version id
        # --persist the data in the output folder = input_csv_folder_path
        # end TODO---------------------------------------------------------------
        # upd_cs_ver_expression_items_dict = code_set_expression_items_json_all_rows[item]
        upd_cs_ver_expression_items_dict: Dict = code_set_expression_items_json_all_rows[premade_codeset_id]
        # update the payload with the codeset_id returned from the

        # DEBUG: Can use this to check to make sure code list is OK:
        # if DEBUG: # updated json data is saved in upd_cs_ver_expression_items_dict
        cs_container_name = container_data_dict[
            'parameters']['ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807']['string']
        print('csContainerName: ' + str(cs_container_name))
        string_list = upd_cs_ver_expression_items_dict[
            'parameters']['ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33']['stringList']['strings']
        print('premade_codeset_id: ' + str(premade_codeset_id))
        print('len(stringList): ' + str(len(string_list)))
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
        # Once the expression items has been added save the enclave concept_id so that we can update the code_sets.csv
        # file update code_sets_df with the enclave_codeset_id column of the  value in the codeset_id retured from the
        # enclave and if needed we can also save the json data in upd_cs_ver_expression_items_dict premade_codeset_id is
        # stored in the codeset_id column in the csv files, save the id in the enclave_codeset_id column update when it
        # was uploaded as well, Stephane 3/15/22
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
    # TODO: fix creates these columns depending on how we're doing indexing: Unnamed: 0	Unnamed: 0.1, etc
    output_filename = 'code_sets.csv'
    code_sets_df.to_csv(os.path.join(input_csv_folder_path, output_filename), index=False, encoding='utf-8')

    return code_sets_df


def _load_standardized_input_df(
    path: str, integer_id_fields=['enclave_codeset_id', 'codeset_id', 'internal_id']
) -> pd.DataFrame:
    """Loads known input dataframe in a standardized way:
        - Sets data types
        - Fill na values"""
    df: pd.DataFrame = pd.read_csv(path).fillna('')

    # Strip: remove the spaces in the beginning and the end of the name
    df.columns.str.lstrip()
    df.columns.str.rstrip()

    # Float->Int: For some reason, was being read with .0's at the end.
    for field in [x for x in integer_id_fields if x in list(df.columns)]:
        df[field] = pd.to_numeric(df[field], errors='coerce')\
            .astype('Int64')

    return df


def left_join_update(df, df2):
    """Does a left join, but where column names are the same, keeps right value if exists, else left value."""
    new_df = df.merge(
        df2, how='left', left_on='internal_id', right_on='codeset_id')

    xy_col_counts: Dict[str, int] = {}
    for col in list(new_df.columns):
        if any([col.endswith(x) for x in ['_x', '_y']]):
            common_col = col[:-2]
            if common_col not in xy_col_counts:
                xy_col_counts[common_col] = 0
            xy_col_counts[common_col] += 1

    xy_cols: List[str] = [k for k, v in xy_col_counts.items() if v == 2]
    for col in xy_cols:
        new_df[col] = new_df[col + '_y'].fillna(new_df[col + '_x'])
        new_df = new_df.drop([col + '_x', col + '_y'], axis=1)

    return new_df


def persist_to_db(code_sets_df: pd.DataFrame) -> pd.DataFrame:
    """Save updated items to persistence layer"""
    # Vars
    join_col = 'codeset_id'
    update_cols = ['enclave_codeset_id', 'enclave_codeset_id_updated_at', 'concept_set_name']

    # Read
    persistence_df = _load_standardized_input_df(CSET_UPLOAD_REGISTRY_PATH)

    # Subset
    try:
        code_sets_df_limited = code_sets_df[[join_col] + update_cols]
    except KeyError:  # if KeyError, `join_col` is an index
        code_sets_df_limited = code_sets_df[update_cols]
    # Join
    persistence_df_new = left_join_update(persistence_df, code_sets_df_limited)

    # Save and return
    persistence_df_new.to_csv(CSET_UPLOAD_REGISTRY_PATH, index=False)
    return persistence_df_new


def _save_csv(
    df: pd.DataFrame, out_format_name: str, in_format_name: str, inpath: str, output_filename: str,
    field_delimiter=','
):
    """Side effects: Save CSV"""
    # date_str = datetime.now().strftime('%Y.%m.%d')
    # out_dir = os.path.join(UPLOADS_DIR, output_name, source_name, date_str, 'output')
    infile_stem = os.path.basename(inpath).replace('.csv', '').replace('.tsv', '')
    out_dir = os.path.join(UPLOADS_DIR, in_format_name, infile_stem, 'transforms', out_format_name)
    os.makedirs(out_dir, exist_ok=True)
    output_format = 'csv' if field_delimiter == ',' else 'tsv' if field_delimiter == '\t' else 'txt'
    outpath = os.path.join(out_dir, f'{output_filename}.{output_format}')
    df.to_csv(outpath, sep=field_delimiter, index=False)


def update_cset_upload_registry_moffit(
    moffit_path: str, registry_path: str = CSET_UPLOAD_REGISTRY_PATH
) -> pd.DataFrame:
    """Update concept set registry file, specifically for moffit entries.
    Side effects: Writes update to registry file w/ any new entries"""
    moffit_df = pd.read_csv(moffit_path).fillna('')
    registry_df = pd.read_csv(registry_path).fillna('')
    registered_moffit_cset_df = registry_df[registry_df['source_id_type'] == MOFFIT_SOURCE_ID_TYPE]
    registered_moffit_ids = [str(x) for x in registered_moffit_cset_df['source_id']]
    moffit_dataset_cset_ids: Set[str] = set([str(int(x)) for x in moffit_df['concept_set_id'].unique() if x != ''])
    new_moffit_cset_ids: List = list(set([x for x in moffit_dataset_cset_ids if x not in registered_moffit_ids]))
    try:  # integers if possible
        new_moffit_cset_ids = [int(x) for x in new_moffit_cset_ids]
    except TypeError:
        pass
    new_moffit_cset_ids.sort()

    new_rows = []
    next_internal_id: int = max(registry_df['internal_id']) + 1
    for _id in new_moffit_cset_ids:
        new_rows.append({
            'source_id_type': 'moffit',
            'source_id': _id,
            # 'source_id_field': '',
            # 'oid': '',
            # 'ccsr_code': '',
            'internal_id': next_internal_id,
            'internal_source': MOFFIT_SOURCE_URL,
            # 'cset_source': '',
            # 'grouped_by_bids': '',
            # 'concept_id': '',
            # 'codeset_id': '',
            # 'enclave_codeset_id': '',
            # 'enclave_codeset_id_updated_at': '',
            # 'concept_set_name': '',
        })
        next_internal_id += 1

    if len(new_rows) > 0:
        new_entries_df = pd.DataFrame(new_rows).fillna('')
        new_registry_df = pd.concat([registry_df, new_entries_df]).fillna('')
        new_registry_df.to_csv(registry_path, index=False)
        return new_registry_df
    return registry_df  # if no new updates


# TODO: repurpose to moffit
# TODO: Make sure all cols are being used
def transform_moffit_to_palantir3file(inpath: str) -> str:
    """Transform Moffit format to Palantir 3 File format."""
    # Vars
    field_delimiter = ','
    out_format_name = 'palantir-three-file'
    in_format_name = 'moffit'
    out_filename1 = 'concept_set_version_item_rv_edited'
    out_filename2 = 'code_sets'
    out_filename3 = 'concept_set_container_edited'
    infile_stem = os.path.basename(inpath).replace('.csv', '').replace('.tsv', '')
    out_dir = os.path.join(UPLOADS_DIR, in_format_name, infile_stem, 'transforms', out_format_name)

    # Read inputs
    inpath = os.path.join(PROJECT_ROOT, inpath) if inpath.startswith('termhub-csets') else inpath
    # df = pd.read_csv(inpath, converters={'concept_set_id': int}).fillna('')  # fails because one row has '' for id
    df = pd.read_csv(inpath).fillna('')
    df = df[df['concept_set_id'] != '']
    df['concept_set_id'] = df['concept_set_id'].astype(int)
    df['concept_set_id'] = df['concept_set_id'].astype(str)
    df = df.applymap(lambda x: x.strip())
    moffit_cset_ids: Set[str] = set([str(int(x)) for x in df['concept_set_id'].unique() if x])

    # Read/update registry
    cset_upload_registry_df: pd.DataFrame = update_cset_upload_registry_moffit(inpath)
    registered_moffit_cset_df = cset_upload_registry_df[
        cset_upload_registry_df['source_id_type'] == MOFFIT_SOURCE_ID_TYPE]
    moffit_id_internal_id_map: Dict[str, str] = dict(zip(
        [str(x) for x in registered_moffit_cset_df['source_id']],
        [str(x) for x in registered_moffit_cset_df['internal_id']]))

    # Transform
    # II. Create & save exports
    _all = {}
    # 1. Palantir enclave table: concept_set_version_item_rv_edited
    rows1 = []
    codeset_id__code__map = {}
    for i, concept_row in df.iterrows():
        internal_id = moffit_id_internal_id_map[str(concept_row['concept_set_id'])]
        code = concept_row['concept_code']
        code_system = concept_row['code_system']

        # This will help us avoid duplicate codes in single concept set
        if internal_id not in codeset_id__code__map:
            codeset_id__code__map[internal_id] = []
        if code not in codeset_id__code__map[internal_id]:
            codeset_id__code__map[internal_id].append(code)
        else:
            continue

        # The 3 fields isExcluded, includeDescendants, and includeMapped, are from OMOP but also in VSAC. If it has
        # ...these 3 options, it is intensional. And when you execute these 3, it is now extensional / expansion.
        # todo: Don't need concept_name?
        row = {
            'codeset_id': internal_id,
            'concept_id': '',  # leave blank for now
            # <non-palantir fields>
            'code': code,
            'codeSystem': code_system,
            # </non-palantir fields>
            'isExcluded': False,
            'includeDescendants': True if code_system == 'SNOMED' else False,
            'includeMapped': False,
            'item_id': str(uuid4()),  # will let palantir verify ID is indeed unique
            'annotation': f'Curated value set: {MOFFIT_PREFIX}',
            # 'created_by': 'DI&H Bulk Import',
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'created_at': _datetime_palantir_format()
        }
        row2 = {}
        for k, v in row.items():
            row2[k] = v.replace('\n', ' - ') if type(v) == str else v
        row = row2
        rows1.append(row)
    df_code_set_members = pd.DataFrame(rows1)
    _all[out_filename1] = df_code_set_members
    _save_csv(df_code_set_members, out_format_name, in_format_name, inpath, out_filename1, field_delimiter)

    # 2. Palantir enclave table: code_sets
    rows2 = []
    for moffit_id in moffit_cset_ids:
        v = 1
        internal_id = moffit_id_internal_id_map[moffit_id]
        cset_row = df[df['concept_set_id'] == moffit_id].iloc[0]
        concept_set_name = f'[{MOFFIT_PREFIX}] ' + cset_row['concept_set_name']
        row = {
            'codeset_id': internal_id,
            'concept_set_name': concept_set_name,
            'concept_set_version_title': concept_set_name + f' (v{str(v)})',
            'project': ENCLAVE_PROJECT_NAME,  # always use this project id for bulk import
            'source_application': '',
            'source_application_version': '',  # nullable
            'created_at': _datetime_palantir_format(),
            'atlas_json': '',  # nullable
            'is_most_recent_version': True,
            'version': v,
            'comments': '',
            'intention': '',  # nullable
            'limitations': '',  # nullable
            'issues': '',  # nullable
            'update_message': 'Initial version.' if v == 1 else '',  # nullable (maybe?)
            # status field stats as appears in the code_set table 2022/01/12:
            # 'status': [
            #     '',  # null
            #     'Finished',
            #     'In Progress',
            #     'Awaiting Review',
            #     'In progress',
            # ][2],
            # status field doesn't show this in stats in code_set table, but UI uses this value by default:
            'status': 'Under Construction',
            'has_review': '',  # boolean (nullable)
            'reviewed_by': '',  # nullable
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'provenance': MOFFIT_SOURCE_URL,
            'atlas_json_resource_url': '',  # nullable
            # null, initial version will not have the parent version so this field would be always null:
            'parent_version_id': '',  # nullable
            # True ( after the import view it from the concept set editor to review the concept set and click done.
            # We can add the comments like we imported from VSAC and reviewed it from the concept set editor. )
            # 1. import 2. manual check 3 click done to finish the definition. - if we want to manually review them
            # first and click Done:
            'is_draft': True,
        }
        rows2.append(row)
    df_code_sets = pd.DataFrame(rows2)
    _all[out_filename2] = df_code_sets
    _save_csv(df_code_sets, out_format_name, in_format_name, inpath, out_filename2, field_delimiter)

    # 3. Palantir enclave table: concept_set_container_edited
    rows3 = []
    for moffit_id in moffit_cset_ids:
        internal_id = moffit_id_internal_id_map[moffit_id]
        cset_row = df[df['concept_set_id'] == moffit_id].iloc[0]
        concept_set_name = f'[{MOFFIT_PREFIX}] ' + cset_row['concept_set_name']
        row = {
            'concept_set_id': internal_id,
            'concept_set_name': concept_set_name,
            'project_id': '',  # nullable
            'assigned_informatician': PALANTIR_ENCLAVE_USER_ID_1,  # nullable
            'assigned_sme': PALANTIR_ENCLAVE_USER_ID_1,  # nullable
            'status': ['Finished', 'Under Construction', 'N3C Validation Complete'][1],
            'stage': [
                'Finished',
                'Awaiting Editing',
                'Candidate for N3C Review',
                'Awaiting N3C Committee Review',
                'Awaiting SME Review',
                'Under N3C Committee Review',
                'Under SME Review',
                'N3C Validation Complete',
                'Awaiting Informatician Review',
                'Under Informatician Review',
            ][1],
            'intention': '',  # nullable
            'n3c_reviewer': '',  # nullable
            'alias': None,  # '' better?
            'archived': False,
            # 'created_by': 'DI&H Bulk Import',
            'created_by': PALANTIR_ENCLAVE_USER_ID_1,
            'created_at': _datetime_palantir_format()
        }

        row2 = {}
        for k, v in row.items():
            row2[k] = v.replace('\n', ' - ') if type(v) == str else v
        row = row2

        rows3.append(row)
    df_code_sets__container_variation = pd.DataFrame(rows3)
    _all[out_filename3] = df_code_sets__container_variation
    _save_csv(df_code_sets__container_variation, out_format_name, in_format_name, inpath, out_filename3, field_delimiter)

    return out_dir


def upload_dataset(input_path: str, format='palantir-three-file', use_cache=False):
    """Main function"""
    if format == 'moffit':
        input_path = transform_moffit_to_palantir3file(input_path)
    code_sets_df: pd.DataFrame = post_to_enclave_from_3csv(input_path)
    persist_to_db(code_sets_df)


def cli():
    """Command line interface for package.

    Side Effects: Executes program."""
    package_description = 'Tool for uploading to the Palantir Foundry enclave.'
    parser = ArgumentParser(description=package_description)

    parser.add_argument(
        '-p', '--input-path',
        help='Path to file or folder to be parsed and uploaded.')
    parser.add_argument(
        '-f', '--format',
        choices=['palantir-three-file', 'moffit'],
        default='palantir-three-file',
        help='The format of the file(s) to be uploaded.\n'
             '- palantir-three-file: Path to folder with 3 files that have specific columns that adhere to concept table data model. These '
             'files must have the following names: i. `code_sets.csv`, ii. `concept_set_container_edited.csv`, iii. '
             '`concept_set_version_item_rv_edited.csv`.\n'
             '- moffit: Has columns concept_set_id, concept_set_name, concept_code, concept_name, code_system.')
    # parser.add_argument(
    #     '-c', '--use-cache',
    #     action='store_true',
    #     help='If present, will check the input file and look at the `enclave_codeset_id` column. If no empty values are'
    #          ' present, this indicates that the `enclave_wrangler` has already been run and that the input file itself '
    #          'can be used as cached data. The only thing that will happen is an update to the persistence layer, '
    #          '(`data/cset.csv` as of 2022/03/18).'),
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    upload_dataset(**kwargs_dict)


if __name__ == '__main__':
    cli()
