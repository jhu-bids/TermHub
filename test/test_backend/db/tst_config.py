"""Tests

How to run:
    python -m unittest discover

TODO: When done: Tst -> Test

todo: would be nice to have a test to make sure nothing in STANDALONE_TABLES doesn't exist in DB, for cleanliness
"""
import os
import sys
import unittest
from pathlib import Path

# noinspection DuplicatedCode
THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.config import DERIVED_TABLE_DEPENDENCY_MAP, STANDALONE_TABLES
from backend.db.utils import list_schema_objects


class TestBackendDbConfig(unittest.TestCase):
    """Test backend/db/config.py"""

    def test_dependency_map(self):
        """Test that DERIVED_TABLE_DEPENDENCY_MAP is not missing tables/views."""
        # Get expected dependent/derived tables/views vs actual tables that might be dependent / have a dependent
        # - gets all table/views in keys or vals of map. Not seem readable/Pythonic though. Surprised it's correct.
        expected = {
            name for sublist in
            [list(DERIVED_TABLE_DEPENDENCY_MAP.keys())] + list(DERIVED_TABLE_DEPENDENCY_MAP.values())
            for name in sublist
        }
        actual = set(list_schema_objects(filter_sequences=True, names_only=True, verbose=False))
        # Adjust for tables known not to be dependent / have a dependent
        actual_adjusted = actual - set(STANDALONE_TABLES)
        # Test diff
        msg = 'In DB but not in config:\n' + str(actual_adjusted - expected) + '\n'\
              'In config but not in DB:\n' + str(expected - actual_adjusted)
        self.assertEqual(expected, actual, msg=msg)


# Uncomment this and run this file and run directly to run all tests
if __name__ == '__main__':
    unittest.main()
