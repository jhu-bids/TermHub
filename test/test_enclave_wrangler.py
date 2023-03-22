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

import pandas as pd
from requests import Response
from sqlalchemy.exc import IntegrityError

from backend.db.utils import get_db_connection, run_sql
from enclave_wrangler.objects_api import cset_version_enclave_to_db, get_new_cset_and_member_objects, \
    update_db_with_new_objects

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))
from enclave_wrangler.actions_api import upload_concept_set_version_draft
from enclave_wrangler.dataset_upload import upload_new_cset_container_with_concepts_from_csv, \
    upload_new_cset_version_with_concepts_from_csv


TEST_INPUT_DIR = os.path.join(TEST_DIR, 'input', 'test_enclave_wrangler')
CSV_DIR = os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')
yesterday: str = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'  # works: 2023-01-01T00:00:00.000Z


class TestEnclaveWrangler(unittest.TestCase):

    def setup(self):  # todo: might want to split up class into smaller use cases to use these
        """always runs first"""
        pass

    def tearDown(self) -> None:  # todo: might want to split up class into smaller use cases to use these
        """always runs last"""
        pass

    # todo: after completing this 'test', create func for it in backend/db and call/assert here
    #  - what is the ultimate goal? how many tables are we refreshing?
    def test_get_new_objects(self):
        """Test get_new_objects()"""
        new_objects: Dict[str, List] = get_new_cset_and_member_objects(since=yesterday)
        # todo: what kind of assert?

    def test_update_db_with_new_objects(self):
        """Test update_db_with_new_objects()"""
        # todo: get latest rows from 4 tables
        pass
        new_objects: Dict[str, List] = get_new_cset_and_member_objects(since=yesterday)
        update_db_with_new_objects(new_objects)
        # todo: check that latest row is different? (assuming that there were actually any new objects
        pass
        # todo: teardown
        #  (a) inserts: delete (can I get PK / index back from query that inserted?
        #  (b) updates: I think I need to back them up before updating them
        #  (c) any way I can do some sort of migrated versioning / rollback of DB instead? (e.g. Alembic)

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

    # todo: adit's recent case 2023/02
    def test_upload_cset_version_from_csv_2(self):
        """Test uploading a new cset version with concepts"""
        pass

    def test_upload_cset_version_from_csv_1(self):
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

    # todo: this test contains concepts, so also uploads a new version. do a case with just container?
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
        print()

    def test_cset_version_enclave_to_db(self):
        """Test codeset_version_enclave_to_db()"""
        with get_db_connection(schema='test_n3c') as con:
            # Failure case
            codeset_id = 1  # exists in test DB
            self.assertRaises(IntegrityError, cset_version_enclave_to_db, con, codeset_id)
            # Success case
            codeset_id = 1049370  # doesn't exist in test DB
            rows1 = [x for x in run_sql(con, 'SELECT codeset_id from code_sets;')]
            cset_version_enclave_to_db(con, codeset_id)
            rows2 = [x for x in run_sql(con, 'SELECT codeset_id from code_sets;')]
            self.assertGreater(len(rows2), len(rows1))
            # Teardown
            run_sql(con, f"DELETE FROM code_sets WHERE codeset_id = '{codeset_id}';")

    def test_cset_container_enclave_to_db(self):  # TODO
        """Test cset_container_enclave_to_db()"""
        pass

    def test_concept_expression_enclave_to_db(self):  # TODO
        """Test cset_container_enclave_to_db()"""
        pass

    def test_concept_member_enclave_to_db(self):  # TODO
        """Test cset_container_enclave_to_db()"""
        pass

if __name__ == '__main__':
    unittest.main()
