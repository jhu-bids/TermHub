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
from enclave_wrangler.objects_api import get_bidirectional_csets_sets

FAIL_MSG = (
    "\n\nFound concept sets in the Enclave that were missing from TermHub.\n"
    "Some possible causes: (i) New csets were added very recently, possibly ass the refresh was running."
    "\n(ii) Csets that were drafts before are now no longer drafts. This will be fixed when via "
    "https://github.com/jhu-bids/TermHub/issues/398\n"
    "Likely this will be fixed when the next refresh runs. If that doesn't happen, or to fix immeediately, you can run:"
    " make fetch-missing-csets\n"
    "The following concept sets are missing from the database: {}")

class TestDatabaseCurrent(unittest.TestCase):
    """Tests for database"""

    @classmethod
    def setUpClass(cls):
        """Fetch cset IDs to used by further tests"""
        cls.db_codeset_ids, cls.enclave_codeset_ids = get_bidirectional_csets_sets()

    def test_all_enclave_csets_in_termhub(self):
        """Test that all Enclave concept sets are in TermHub"""
        missing_ids_from_db: Set[int] = self.enclave_codeset_ids.difference(self.db_codeset_ids)
        # todo?: some analysis may be uesful here?
        # if missing_ids_from_db:
        #     missing_from_db = [cset for cset in enclave_codesets if cset['codesetId'] in missing_ids_from_db]
        #     drafts = [cset for cset in missing_from_db if cset['isDraft']]
        #     notdrafts = [cset for cset in missing_from_db if not cset['isDraft']]
        self.assertEqual(missing_ids_from_db, set(), msg=FAIL_MSG.format(missing_ids_from_db))

    def test_all_termhub_csets_in_enclave(self):
        """Test that TermHub concept sets are in the Enclave"""
        extra_in_db: Set[int] = self.db_codeset_ids.difference(self.enclave_codeset_ids)
        # todo: analyze: get these from database and figure out what's up with them
        # if extra_in_db:
        self.assertEqual(extra_in_db, set())
