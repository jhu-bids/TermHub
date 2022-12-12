"""Tests

How to run:
    python -m unittest discover

TODO's
 - 1. Test framework: Current implementation is ad-hoc for purposes of development.
 - 2. Change from validate to apply, or do both
"""
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
from requests import Response

from enclave_wrangler.objects_api import EnclaveClient

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))
from enclave_wrangler.actions_api import delete_concept_set_version, upload_concept_set_container, \
    upload_concept_set_version
from enclave_wrangler.utils import make_read_request, make_request
from enclave_wrangler.dataset_upload import post_to_enclave_from_3csv, upload_new_cset_version_with_concepts
from enclave_wrangler.config import PALANTIR_ENCLAVE_USER_ID_1


TEST_INPUT_DIR = os.path.join(TEST_DIR, 'input', 'test_enclave_wrangler')


# TODO use proper teardown() methods
class TestEnclaveWrangler(unittest.TestCase):

    def setup(self):
        """always runs first"""
        pass

    def tearDown(self) -> None:
        """always runs last"""
        pass

    def test_upload(self):
        """Test uploading a new cset version with concepts"""
        csv_dir = os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')
        fname = os.path.join(csv_dir, 'type-2-diabetes-mellitus.csv')
        df = pd.read_csv(fname).fillna('')
        omop_concepts = df[[
            'concept_id',
            'includeDescendants',
            'isExcluded',
            'includeMapped',
            'annotation']].to_dict(orient='records')
        new_version = {
            "omop_concepts": omop_concepts,
            "provenance": "Created through TermHub.",
            "concept_set_name": "[DM]Type2 Diabetes Mellitus",
            "limitations": "",
            "intention": "",
            "on_behalf_of": os.getenv('ON_BEHALF_OF')
        }

        d: Dict = upload_new_cset_version_with_concepts(**new_version, validate_first=False)
        responses: Dict[str, Union[Response, List[Response]]] = d['responses']
        version_id: int = d['versionId']
        for response in responses.values():
            if isinstance(response, list):  # List[Response] returned by concepts upload
                for response_i in response:
                    self.assertLess(response_i.status_code, 400)
            else:
                self.assertLess(response.status_code, 400)

        # Teardown
        # TODO: After getting to work, turn validate_first=False
        response: Response = delete_concept_set_version(version_id, validate_first=True)
        self.assertLess(response.status_code, 400)


    # TODO
    # noinspection PyUnusedLocal
    def test_upload_3_csv_format(self, inpath=os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')):
        """Test upload of a new dataset"""
        # todo: Can add this test by composing other non-validation tests (then, remove 'PyUnusedLocal' line)
        # todo: can just not create container for now, and test simply (i) add/delete versions, (ii) add/delete concepts

        # TODO: use dataset_upload to upload a palantir-3-file set
        # post_to_enclave_from_3csv(inpath, create_cset_container=False, create_cset_versions=False)

        # TODO: do actual uploads as well; but this requires "teardown" completion first
        # post_to_enclave(inpath)

        # TODO: teardown: "apiName": "archive-concept-set",
        #     {
        #       "apiName": "archive-concept-set",
        #       "description": "Sets Concept Set 'archived' property to true so that it no longer appears in browser",
        #       "rid": "ri.actions.main.action-type.cbc3643b-cca4-4772-ae2d-ae7036a6798b",
        #       "parameters": {
        #         "concept-set": {
        #           "description": "",
        #           "baseType": "OntologyObject"
        #         }
        #       }
        #     },
        pass

    # TODO: teardown: "apiName": "archive-concept-set",
    #     {
    #       "apiName": "archive-concept-set",
    #       "description": "Sets Concept Set 'archived' property to true so that it no longer appears in browser",
    #       "rid": "ri.actions.main.action-type.cbc3643b-cca4-4772-ae2d-ae7036a6798b",
    #       "parameters": {
    #         "concept-set": {
    #           "description": "",
    #           "baseType": "OntologyObject"
    #         }
    #       }
    #     },
    def test_upload_concept_set_container(self, user_id=PALANTIR_ENCLAVE_USER_ID_1):
        response: Response = upload_concept_set_container(
            concept_set_id='x', intention='x', research_project='x', assigned_sme=user_id,
            assigned_informatician=user_id)
        # self.assertTrue('result' in response and not response['result'] == 'VALID')
        if not('result' in response and response['result'] == 'VALID'):
            print('Failure: test_upload_concept_set\n', response, file=sys.stderr)

    # TODO: complete test
    # TODO: teardown: "apiName": "delete-omop-concept-set-version-item",
    #     {
    #       "apiName": "delete-omop-concept-set-version-item",
    #       "description": "",
    #       "rid": "ri.actions.main.action-type.231fc70d-a9c4-498e-bc5f-cf38046c9217",
    #       "parameters": {
    #         "concept-set-version-item": {
    #           "description": "",
    #           "baseType": "Array<OntologyObject>"
    #         }
    #       }
    #     },
    def test_add_concept_to_cset(self):
        pass
        # response = add_concepts_via_array()
        # # self.assertTrue('result' in response and not response['result'] == 'VALID')
        # if not('result' in response and response['result'] == 'VALID'):
        #     print('Failure: test_upload_concept_set\n', response, file=sys.stderr)

    # TODO: teardown: "apiName": "delete-omop-concept-set-version",
    #     {
    #       "apiName": "delete-omop-concept-set-version",
    #       "description": "Do not forget to the flag 'Is Most Recent Version' of the previous Concept Set Version to True!",
    #       "rid": "ri.actions.main.action-type.93b82f88-bd55-4daf-a0f9-f6537bf2bce1",
    #       "parameters": {
    #         "omop-concept-set": {
    #           "description": "",
    #           "baseType": "OntologyObject"
    #         },
    #         "expression-items": {
    #           "description": "",
    #           "baseType": "Array<OntologyObject>"
    #         }
    #       }
    #     },
    def test_upload_concept_set_version(self):
        response: Response = upload_concept_set_version(
            domain_team='x', provenance='x', current_max_version=2.1, concept_set='x', annotation='x', limitations='x',
            intention='x', base_version=1, intended_research_project='x', version_id=1, authority='x')
        # self.assertTrue('result' in response and not response['result'] == 'VALID')
        self.assertLess(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
