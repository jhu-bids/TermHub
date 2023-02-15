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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Union

from requests import Response

from enclave_wrangler.objects_api import EnclaveClient

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))
from enclave_wrangler.actions_api import get_concept_set_version_expression_items, get_concept_set_version_members, \
    upload_concept_set_container, \
    upload_concept_set_version
from enclave_wrangler.dataset_upload import upload_new_cset_version_with_concepts_from_csv
from enclave_wrangler.config import PALANTIR_ENCLAVE_USER_ID_1


TEST_INPUT_DIR = os.path.join(TEST_DIR, 'input', 'test_enclave_wrangler')
CSV_DIR = os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')

# TODO use proper teardown() methods
class TestEnclaveWrangler(unittest.TestCase):

    def setup(self):
        """always runs first"""
        pass

    def tearDown(self) -> None:
        """always runs last"""
        pass

    def test_upload(self):
        """Test uploading a new cset version with concepts
        using:
        https://github.com/jhu-bids/TermHub/blob/develop/test/input/test_enclave_wrangler/test_dataset_upload/type-2-diabetes-mellitus.csv
        file format docs:
        https://github.com/jhu-bids/TermHub/tree/develop/enclave_wrangler
        """
        path = os.path.join(CSV_DIR, 'type-2-diabetes-mellitus.csv')
        # TODO: temp validate_first until fix all bugs
        d: Dict = upload_new_cset_version_with_concepts_from_csv(path, validate_first=True)
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
        # TODO: @jflack4, this delete doesn't work because the cset draft has been finalized
        # if False:   # just don't do this till it gets fixed
        #     response: Response = delete_concept_set_version(version_id, validate_first=True)
        #     self.assertLess(response.status_code, 400)

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
        # noinspection PyUnresolvedReferences
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

    # todo: after completing this 'test', create func for it in backend/db and call/assert here
    #  - what is the ultimate goal? how many tables are we refreshing?
    def test_get_new_objects(self):
        """Test get_new_objects()"""
        client = EnclaveClient()
        # https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/#filtering-objects
        # https://unite.nih.gov/workspace/data-integration/restricted-view/preview/ri.gps.main.view.af03f7d1-958a-4303-81ac-519cfdc1dfb3
        example_datetime = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'  # works: 2023-01-01T00:00:00.000Z

        # 1. Fetch data
        # Concept set versions
        new_csets: List[Dict] = client.get_objects_by_type(
            'OmopConceptSet', since_datetime=example_datetime, return_type='list_dict')

        # Containers
        containers_ids = [x['properties']['conceptSetNameOMOP'] for x in new_csets]
        container_params = ''.join([f'&properties.conceptSetId.eq={x}' for x in containers_ids])
        new_containers: List[Dict] = client.get_objects_by_type(
            'OMOPConceptSetContainer', return_type='list_dict', query_params=container_params, verbose=True)

        # Expression items & concept set members
        new_csets2: List[Dict] = []
        for cset in new_csets:
            version: int = cset['properties']['codesetId']
            cset['expression_items'] = get_concept_set_version_expression_items(version, return_detail='full')
            cset['members'] = get_concept_set_version_members(version, return_detail='full')
            new_csets2.append(cset)

        # 2. Database updates
        # TODO: (i) What tables to update after this?, (ii) anything else to be done?. Iterate over:
        #  - new_containers: * new containers, * delete & updates to existing containers
        #  - new_csets2:
        #    - the cset properties itself
        #    - expression_items: we might want to delete its previous items as well, because of possible changes
        #      does expression item ID change when you change one of its flags?
        #    - members
        pass

        print()


if __name__ == '__main__':
    unittest.main()
