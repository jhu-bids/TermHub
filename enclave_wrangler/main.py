"""Main module
# TODO's:
- For mappings, I believe Amin will be providing us to .parquet files. We can read with pandas: https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html

Resources
- Validate URL (for testing POSTs without it actually taking effect): https://unite.nih.gov/actions/api/actions/validate
- Wiki article on how to create these JSON: https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs
"""
import os
from datetime import datetime, timezone

import requests
import pandas as pd

from enclave_wrangler.config import config


# USER1: This is an actual ID to a valid user in palantir, who works on our BIDS team.
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
VSAC_LABEL_PREFIX = '[VSAC Bulk-Import test] '
# API_URL query params:
# 1. ?synchronousPropagation=false: Not sure what this does or if it helps.
API_URL = 'https://unite.nih.gov/actions/api/actions'
API_VALIDATE_URL = 'https://unite.nih.gov/actions/api/actions/validate'


def _datetime_palantir_format() -> str:
    """Returns datetime str in format used by palantir data enclave
    e.g. 2021-03-03T13:24:48.000Z (milliseconds allowed, but not common in observed table)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'


def run(input_csv_folder_path):
    """Main function"""
    # code_sets_df = pd.read_csv(os.path.join(input_csv_folder_path, 'code_sets.csv')).fillna('')
    concept_set_container_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    # concept_set_version_item_rv_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')

    # TODO: We're not 100% sure how to submit multiple containers in a single request yet
    concept_set_container_edited_json_all_rows = []
    for index, row in concept_set_container_edited_df.iterrows():
        concept_set_container_edited_json_single_row = {
            "actionTypeRid": "ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae",
            "parameters": {
                # 7/13 required fields:
                # <concept name i.e. [VSAC BulkImport - Test] concept name goes here>
                "ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807": {
                    "type": "string",
                    "string": row['concept_set_name']
                },
                # <intention text value goes here>
                # -
                "ri.actions.main.parameter.9e33b4d9-c7eb-4f27-81cd-152cc89f334b": {
                    "type": "string",
                    "string": row['intention']
                },
                # <assigned_informatician>
                "ri.actions.main.parameter.28448734-2b6c-41e7-94aa-9f0d2ac1936f": {
                    "type": "string",
                    "string": row['created_by']
                },
                # <assigned_sme>
                "ri.actions.main.parameter.f04fd21f-4c97-4640-84e3-f7ecff9d1018": {
                    # "type": "string",
                    # # Which CSV / table field corresponds to this param??
                    # "string": ''
                    "null": {},
                    "type": "null"
                },
                # <status value set to>Under Construction
                "ri.actions.main.parameter.2b3e7cd9-6704-40a0-9383-b6c734032eb3": {
                    "type": "string",
                    "string": row['status']
                },
                # <stage value set to>Awaiting Edition
                "ri.actions.main.parameter.02dbf67e-0acc-43bf-a0a9-cc8d1007771b": {
                    "type": "string",
                    # Which CSV / table field corresponds to this param??
                    "string": 'Awaiting Edition'
                },
                # <project_id>, e.g. [RP-4A9E27]
                "ri.actions.main.parameter.a3eace19-c42d-4ff5-aa63-b515f3f79bdd": {
                    "objectLocator": {
                        "objectTypeId": "research-project",
                        "primaryKey": {
                            "research_project_uid": {
                                "string": row['project_id'],
                                "type": "string"
                            }
                        }
                    },
                    "type": "objectLocator"
                },
                # 6/13 Optional fields not included:
                # - alias
                # - created_at
                # - n3c_reviewer
                # - ???
                # - ???
                # - ???
            }
            # This field was not in Amin's working example JSON, so commenting it out - Joe:
            # "ri.actions.main.parameter.36a1670f-49ca-4491-bb42-c38707bbcbb2": {
            #     "type": "objectLocator",
            #     "objectLocator": {
            #         "objectTypeId": "omop-concept-set-container",
            #         "primaryKey": {
            #             # <[VSAC] VSAC Concept set name>
            #             "concept_set_id": {
            #                 "type": "string",
            #                 "string": row['concept_set_name']
            #             }
            #         }
            #     }
            # }
        }
        concept_set_container_edited_json_all_rows.append(concept_set_container_edited_json_single_row)

    # Do a test first using 'valdiate'
    api_url = API_VALIDATE_URL
    data = concept_set_container_edited_json_all_rows[0]
    header = {
        'authorization': f'Bearer {config["PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"]}'
        # 'Authentication': f'Bearer {config["PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"]}'
    }
    response = requests.post(
        api_url,
        data=data,
        headers=header)
    response_json = response.json()
    print(response_json)

    # TODO: After successful validate, do real POSTs (check if they exist first?
    print()


if __name__ == '__main__':
    run(None)
