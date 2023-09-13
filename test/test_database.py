"""Tests

Can run all tests in all files by running this from root of TermHub:
    python -m unittest discover
"""
import os
import sys
import unittest
from pathlib import Path
from typing import Set

TEST_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
from enclave_wrangler.objects_api import find_and_add_missing_csets_to_db, get_bidirectional_csets_sets

# TODO: temp
# Note: Ad hoc import: On 2023/09/12, we found 93 missing csets. The below code was used to import them.
if __name__ == '__main__':
    find_and_add_missing_csets_to_db()

class TestDatabaseCurrent(unittest.TestCase):
    """Tests for database"""

    @classmethod
    def setUpClass(cls):
        """Fetch cset IDs to used by further tests"""
        cls.db_codeset_ids, cls.enclave_codeset_ids = get_bidirectional_csets_sets()
        pass

    def test_all_enclave_csets_in_termhub(self):
        """Test that all Enclave concept sets are in TermHub"""
        missing_ids_from_db: Set[int] = self.enclave_codeset_ids.difference(self.db_codeset_ids)
        # todo?: some analysis may be uesful here?
        # if missing_ids_from_db:
        #     missing_from_db = [cset for cset in enclave_codesets if cset['codesetId'] in missing_ids_from_db]
        #     drafts = [cset for cset in missing_from_db if cset['isDraft']]
        #     notdrafts = [cset for cset in missing_from_db if not cset['isDraft']]
        self.assertEqual(missing_ids_from_db, set())

    def test_all_termhub_csets_in_enclave(self):
        """Test that TermHub concept sets are in the Enclave"""
        extra_in_db: Set[int] = self.db_codeset_ids.difference(self.enclave_codeset_ids)
        # todo: analyze: get these from database and figure out what's up with them
        # if extra_in_db:
        self.assertEqual(extra_in_db, set())