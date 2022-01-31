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
from enclave_wrangler.enclave_api import get_cs_container_data

PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
VSAC_LABEL_PREFIX = '[VSAC Bulk-Import test1] '
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
    ##does not work in pc...
    concept_set_container_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_container_edited.csv')).fillna('')
    #concept_set_container_edited_df = pd.read_csv(os.path.join('C:\git\ValueSet-Tools\input\enclave_3_csv_files', 'concept_set_container_edited.csv')).fillna('')

    # concept_set_version_item_rv_edited_df = pd.read_csv(os.path.join(input_csv_folder_path, 'concept_set_version_item_rv_edited.csv')).fillna('')

    # TODO: We're not 100% sure how to submit multiple containers in a single request yet
    concept_set_container_edited_json_all_rows = []
    concept_set_container_version_all_rows = []
    concept_set_container_code_expression_all_rows = []
    for index, row in concept_set_container_edited_df.iterrows():
        data = get_cs_container_data(row['concept_set_name'])
        ##
        concept_set_container_edited_json_all_rows.append(data)

    # Do a test first using 'valdiate'
    api_url = API_VALIDATE_URL
    data = concept_set_container_edited_json_all_rows[0]
    header = {
        'authorization': f'Bearer {config["PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"]}',
        # 'Authentication': f'Bearer {config["PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"]}'
        'content-type': f'application/json'
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
