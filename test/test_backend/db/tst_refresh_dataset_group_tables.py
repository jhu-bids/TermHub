"""Tests

How to run:
    python -m unittest discover

todo's
 - Improve test input files by picking out some concept IDs from concept.csv and then filtering rows from other files
TODO: When done: Tst -> Test
"""
import os
import sys
from pathlib import Path
from typing import Dict, List

from sqlalchemy import RowMapping

from backend.db.refresh_dataset_group_tables import refresh_dataset_group_tables
from backend.db.utils import get_db_connection, get_ddl_statements, sql_query
from enclave_wrangler.config import DATASET_GROUPS_CONFIG

# noinspection DuplicatedCode
THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

THIS_INPUT_DIR = THIS_DIR / 'input' / 'test_refresh_dataset_group_tables'
DOWNLOAD_DIR = PROJECT_ROOT / 'termhub-csets' / 'datasets' / 'prepped_files'
TEST_SCHEMA = 'test_n3c'


# todo: could create some more test cases (i) too many expressions, (ii) >100k members, (iii) 0 members?
class TestRefreshDatasetGroupTables:
# class TestRefreshDatasetGroupTables(DbRefreshTestWrapper):
    """Test refresh_dataset_group_tables.py"""

    tables_by_group: Dict[str, List[str]] = {k: v['tables'] for k, v in DATASET_GROUPS_CONFIG.items()}

    @classmethod
    def set_up_vocab(cls):
        """Set up mock vocab tables
        todo: alternatively, *could* be better to take first 50 rows of tables from n3c, as in DbRefreshTestWrapper, and
         write those tables to CSVs in DOWNLOAD_DIR first. Then can get rid of input/ files."""
        n_lines_for_inputs = 50

        for group, tables in cls.tables_by_group.items():
            input_dir = THIS_INPUT_DIR / group
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)

            missing_inputs = set([f'{x}.csv' for x in tables]).difference(set(os.listdir(input_dir)))
            if missing_inputs:
                # Download dataasets if necessary
                missing_downloads = set([f'{x}.csv' for x in tables]).difference(set(os.listdir(DOWNLOAD_DIR)))
                if missing_downloads:
                    refresh_dataset_group_tables(
                        [group], download_only=True, schema=TEST_SCHEMA, test_run_dont_mark_updated=True)
                # Create inputs
                for table in tables:
                    with open(DOWNLOAD_DIR / f'{table}.csv', 'r') as f:
                        sample_lines = f.readlines()[:n_lines_for_inputs]
                    with open(input_dir / f'{table}.csv', 'w') as f:
                        f.writelines(sample_lines)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.set_up_vocab()

    def tst_refresh_dataset_group_tables(self):
        """Test refresh_dataset_group_tables()"""
        for group, tables in self.tables_by_group.items():

            # TODO: temp #1
            if group == 'vocab':
                continue

            # TODO: temp: #1 turn skip_downloads back to True after fixing parquet issue
            # Refresh tables for given dataset group
            refresh_dataset_group_tables(
                [group], skip_downloads=False, schema=TEST_SCHEMA, alternate_dataset_dir=THIS_INPUT_DIR / group,
                test_run_dont_mark_updated=True)

            # Analyze results and test
            index_statements_all: List[str] = get_ddl_statements(TEST_SCHEMA, ['indexes'], return_type='flat')
            with get_db_connection(schema=TEST_SCHEMA) as con:
                for table in tables:
                    # Analyze
                    indexes_expected: List[str] = [x for x in index_statements_all if f'{TEST_SCHEMA}.{table}(' in x]
                    indexes_and_pkeys: List[RowMapping] = sql_query(con, f"""
                        SELECT indexname, indexdef
                        FROM pg_indexes
                        WHERE tablename = '{table}' AND schemaname = '{TEST_SCHEMA}';""")
                    pkeys: List[RowMapping] = [x for x in indexes_and_pkeys if 'pkey' in x['indexname']]

                    # Test
                    # TODO: revert below when done (Tst -> Test)
                    # - test 1: Expected indexes on each table
                    assert len(indexes_expected) == len(indexes_and_pkeys) - len(pkeys)
                    # self.assertEqual(len(indexes_expected), len(indexes_and_pkeys) - len(pkeys))
                    # - test 2: Concept table only: Has primary key(s)
                    if table == 'concept':
                        # self.assertGreater(len(pkeys), 0)
                        assert len(pkeys) > 0


# Uncomment this and run this file and run directly to run all tests
if __name__ == '__main__':
    # unittest.main()
    TestRefreshDatasetGroupTables().tst_refresh_dataset_group_tables()
