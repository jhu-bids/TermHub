"""Tests

Can run all tests in all files by running this from root of TermHub:
    python -m unittest discover
"""
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
from requests import Response

THIS_TEST_DIR = Path(os.path.dirname(__file__))
TEST_DIR = THIS_TEST_DIR.parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
TEST_INPUT_DIR = THIS_TEST_DIR / 'input'

from enclave_wrangler.dataset_upload import upload_new_cset_container_with_concepts_from_csv, \
    upload_new_cset_version_with_concepts_from_csv


class TestDatasetUpload(unittest.TestCase):
    def test_upload_cset_container_from_csv(self):
        """Test uploading a concept set container from CSV"""
        # response: Response = upload_concept_set_container(
        #     concept_set_id='x', intention='x', research_project='x', assigned_sme=user_id,
        #     assigned_informatician=user_id)
        # if not('result' in response and response['result'] == 'VALID'):
        #     print('Failure: test_upload_concept_set\n', response, file=sys.stderr)
        inpath = os.path.join(TEST_INPUT_DIR, 'test_upload_cset_container_from_csv', 'new_container.csv')
        df = pd.read_csv(inpath).fillna('')
        response: Dict = upload_new_cset_container_with_concepts_from_csv(df=df)
        print(response)


    # TODO #1: for "success case", these things that aren't in the DB yet will be, so will need to instead
    #  (a) fetch recent objects, and just pick 1 if anything new exists, (b) (best) fetch junk concept set version etc
    #  (c) We could pick an 'archived' concept set container. After we fetch it, turn the 'archived' flag off.

    def _test_upload_cset_version_from_csv(self, path: str):
        """Test uploading a new cset version with concepts
        file format docs: https://github.com/jhu-bids/TermHub/tree/develop/enclave_wrangler"""
        # TODO: temp validate_first until fix all bugs
        # TODO: Will this work if UUID is different?
        d: Dict = upload_new_cset_version_with_concepts_from_csv(path, validate_first=True)
        d = list(d.values())[0]
        responses: Dict[str, Union[Response, List[Response]]] = d['responses']
        version_id: int = d['versionId']
        print(f'Uploaded new version with ID: {version_id}')
        for response in responses.values():
            if isinstance(response, list):  # List[Response] returned by concepts upload
                for response_i in response:
                    self.assertLess(response_i.status_code, 400)
            else:
                self.assertLess(response.status_code, 400)

        # Teardown
        # TODO: After getting to work, turn validate_first=False
        # TODO: @jflack4, this delete doesn't work because the cset draft has been finalized
        # if False:   # just don't do this till it gets fixed
        #     response: Response = delete_concept_set_version(version_id, validate_first=True)
        #     self.assertLess(response.status_code, 400)

    # todo?: adit's recent case 2023/02
    def test_upload_cset_version_from_csv2(self):
        """Case 2"""
        path = os.path.join(TEST_INPUT_DIR, 'test_upload_cset_version_from_csv2', 'new_version.csv')
        self._test_upload_cset_version_from_csv(path)

    def test_upload_cset_version_from_csv(self):
        """Case 1
        using: https://github.com/jhu-bids/TermHub/blob/develop/test/input/test_enclave_wrangler/test_dataset_upload/type-2-diabetes-mellitus.csv
        """
        path = os.path.join(TEST_INPUT_DIR, 'test_upload_cset_version_from_csv', 'type-2-diabetes-mellitus.csv')
        self._test_upload_cset_version_from_csv(path)