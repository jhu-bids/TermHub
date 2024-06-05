"""Tests for the Enclave actions API"""
import os
import sys
import unittest
from pathlib import Path
from requests import Response

THIS_TEST_DIR = Path(os.path.dirname(__file__))
TEST_DIR = THIS_TEST_DIR.parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from enclave_wrangler.actions_api import upload_concept_set_version_draft


class TestActionsApi(unittest.TestCase):

    @unittest.skip("Skipping tests for incomplete feature. See: https://github.com/jhu-bids/TermHub/issues/799")
    def test_upload_concept_set_version(self):
        response: Response = upload_concept_set_version_draft(
            domain_team='x', provenance='x', current_max_version=2.1, concept_set='x', annotation='x', limitations='x',
            intention='x', base_version=1, intended_research_project='x', version_id=1, authority='x')
        # self.assertTrue('result' in response and not response['result'] == 'VALID')
        self.assertLess(response.status_code, 400)

    # TODO: teardown: "apiName": "archive-concept-set", (for version or container?)
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