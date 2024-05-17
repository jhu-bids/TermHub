"""Tests for refreshing of dataset groups

How to run:
    python -m unittest discover

todo's
 - Improve test input files by picking out some concept IDs from concept.csv and then filtering rows from other files
"""
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List

from sqlalchemy import RowMapping

# noinspection DuplicatedCode
THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.refresh_dataset_group_tables import load_dataset_group, refresh_dataset_group_tables
from backend.db.utils import SCHEMA, get_db_connection, get_ddl_statements, sql_query
from enclave_wrangler.config import DATASET_GROUPS_CONFIG
from test.utils_db_refresh_test_wrapper import DbRefreshTestWrapper

THIS_INPUT_DIR = THIS_DIR / 'input' / 'test_refresh_dataset_group_tables'
DOWNLOAD_DIR = PROJECT_ROOT / 'termhub-csets' / 'datasets' / 'prepped_files'
TEST_SCHEMA = 'test_n3c'
TABLES_BY_GROUP: Dict[str, List[str]] = {k: v['tables'] for k, v in DATASET_GROUPS_CONFIG.items()}


def _set_up_vocab():
    """Set up mock vocab tables
    todo: alternatively, *could* be better to take first 50 rows of tables from n3c, as in DbRefreshTestWrapper, and
     write those tables to CSVs in DOWNLOAD_DIR first. Then can get rid of input/ files."""
    n_lines_for_inputs = 50

    for group, tables in TABLES_BY_GROUP.items():
        input_dir = THIS_INPUT_DIR / group
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)

        missing_inputs = set([f'{x}.csv' for x in tables]).difference(set(os.listdir(input_dir)))
        if missing_inputs:
            # Download dataasets if necessary
            missing_downloads = set([f'{x}.csv' for x in tables]).difference(set(os.listdir(DOWNLOAD_DIR)))
            if missing_downloads:
                refresh_dataset_group_tables(
                    [group], download_only=True, schema=TEST_SCHEMA)
            # Create inputs
            for table in tables:
                with open(DOWNLOAD_DIR / f'{table}.csv', 'r') as f:
                    sample_lines = f.readlines()[:n_lines_for_inputs]
                with open(input_dir / f'{table}.csv', 'w') as f:
                    f.writelines(sample_lines)


def _analyze_group_tables(group_name: str, schema: str = TEST_SCHEMA) -> Dict:
    """Analyze tables for a given dataset group
    todo: this smells like it should maybe be refactored into a pure function"""
    tables: List[str] = TABLES_BY_GROUP[group_name]
    table_data = {}
    index_statements_all: List[str] = get_ddl_statements(schema, ['indexes'], return_type='flat')
    with get_db_connection(schema=schema) as con:
        for table in tables:
            indexes_expected: List[str] = [x for x in index_statements_all if f'{schema}.{table}(' in x]
            indexes_and_pkeys: List[RowMapping] = sql_query(con, f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{table}' AND schemaname = '{schema}';""")
            pkeys: List[RowMapping] = [x for x in indexes_and_pkeys if 'pkey' in x['indexname']]
            table_data[table] = {
                'indexes_expected': indexes_expected,
                'indexes_and_pkeys': indexes_and_pkeys,
                'pkeys': pkeys
            }
    return table_data

class DatasetGroupAnalysis(unittest.TestCase):

    def _check_indexes_and_pkeys(self, group_name: str, schema: str = TEST_SCHEMA):
        """Run tests on given dataset group and schema"""
        table_data: Dict = _analyze_group_tables(group_name, schema)
        for table, data in table_data.items():
            # - test: Expected indexes on each table
            self.assertEqual(len(data['indexes_expected']), len(data['indexes_and_pkeys']) - len(data['pkeys']))
            # - test: Concept table only: Has primary key(s)
            if table == 'concept':
                self.assertGreater(len(data['pkeys']), 0)


# todo: could create some more test cases (i) too many expressions, (ii) >100k members, (iii) 0 members?
class TestRefreshDatasetGroupTables(DbRefreshTestWrapper, DatasetGroupAnalysis):
    """Test refresh_dataset_group_tables.py"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _set_up_vocab()

    def test_load_dataset_group(self):
        """"Test load_dataset_group(). This is what does the most work in refresh_dataset_group_tables()."""
        for group_name in TABLES_BY_GROUP.keys():
            load_dataset_group(group_name, TEST_SCHEMA, THIS_INPUT_DIR / group_name)
            self._check_indexes_and_pkeys(group_name)


class TestCurrentDatasetGroupSetup(DatasetGroupAnalysis):
    """Test current tables setup for group (indexes and, if applicable, primary keys)"""

    def test_current_vocab(self):
        """Test group: vocab"""
        self._check_indexes_and_pkeys('vocab', SCHEMA)

    def test_current_counts(self):
        """Test group: counts"""
        self._check_indexes_and_pkeys('counts', SCHEMA)


# Uncomment this and run this file and run directly to run all tests
if __name__ == '__main__':
    unittest.main()
