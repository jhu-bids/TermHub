"""Tests

How to run:
    python -m unittest discover

TODO's
 - 1. Test framework: Current implementation is ad-hoc for purposes of development.
 - 2. Change from validate to apply, or do both
"""
import os
import pickle
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
from requests import Response
from sqlalchemy.exc import IntegrityError

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))

TEST_INPUT_DIR = os.path.join(TEST_DIR, '../input', 'test_enclave_wrangler')
TEST_SCHEMA = 'test_n3c'
yesterday: str = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'  # works: 2023-01-01T00:00:00.000Z


class TestEnclaveWrangler(unittest.TestCase):

    # todo: after completing this 'test', create func for it in backend/db and call/assert here
    #  - what is the ultimate goal? how many tables are we refreshing?
    # todo: also add test for get_new_objects()
    # def test_get_new_csets_and_members(self):
    #     """Test test_get_new_csets_and_members()"""
    #     csets_and_members: Dict[str, List] = fetch_cset_and_member_objects(since=yesterday)
    #     # todo: what kind of assert?

    # TODO: Seems to be failing now because using test_n3c instead of n3c even though con schema=TEST_SCHEMA

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

    # todo: this test contains concepts, so also uploads a new version. do a case with just container?

# def test_concept_members_enclave_to_db(self):
#     """Test concept_set_members_enclave_to_db()
#     todo: See #1 above
#     todo: remove this test? concept_set_members_enclave_to_db() now deprecated
#      if keeping it, it needs to be refactored because now 'container' is a required parameter"""
#     table = 'concept_set_members'
#     with get_db_connection(schema=TEST_SCHEMA) as con:
#         # Failure case: exists in test DB
#         cset_members_fail = {
#             'codeset_id': 479356,
#             'concept_id': 3018737
#         }
#         self.assertRaises(IntegrityError, concept_set_members_enclave_to_db, con, cset_members_fail['codeset_id'],
#                           cset_members_fail['concept_id'], False)
#
#         # Success case:  doesn't exist in test DB
#         cset_members_succeed = {
#             'codeset_id': 573795,
#             'concept_id': 22557
#         }
#         n1: int = sql_count(con, table)
#         concept_set_members_enclave_to_db(
#             con, cset_members_succeed['codeset_id'], cset_members_succeed['concept_id'], members_table_only=True)
#         n2: int = sql_count(con, table)
#         self.assertGreater(n2, n1)
#         # Teardown
#         run_sql(con, f"DELETE FROM {table} WHERE codeset_id = '{cset_members_succeed['codeset_id']}' "
#                      f"AND concept_id = '{cset_members_succeed['concept_id']}';")

# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()
