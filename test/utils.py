"""Utils for tests

todo: This is rather heavy, to do reset_all_test_tables() at the beginning of each backend DB related test that depends
 on the test_n3c schema. For each such test class, it will remake the entire test schema. But I'm not sure of a good way
 to avoid."""
import os
import sys
from pathlib import Path
from typing import List

THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.utils import SCHEMA, get_db_connection, get_ddl_statements, list_tables, list_views, run_sql

N_ROWS_TEST_TABLES = 50
TEST_SCHEMA = f'test_{SCHEMA}'


# todo: various sub-tasks in https://github.com/jhu-bids/TermHub/issues/804
def remake_test_schema(schema: str = SCHEMA, test_schema: str = TEST_SCHEMA, n_rows=N_ROWS_TEST_TABLES):
    """Reset entire test_schema, copying over n_rows from all tables in schema."""
    with get_db_connection(schema='') as con:
        run_sql(con, f'DROP SCHEMA IF EXISTS {test_schema} CASCADE;\n'
                     f'CREATE SCHEMA {test_schema};')
    with get_db_connection(schema=schema) as con:
        tables = list_tables(con, filter_temp_refresh_tables=True)
    with get_db_connection(schema=test_schema) as con:
        for table in tables:
            run_sql(con, f'DROP TABLE IF EXISTS {test_schema}.{table} CASCADE;')
    _copy_over_tables(tables, schema, test_schema, n_rows)


# todo: remove? Unused: This func may never be useful, because it can't keep test schema in sync: https://github.com/jhu-bids/TermHub/pull/577#discussion_r1412914522
def populate_missing_test_tables(schema: str = SCHEMA, test_schema: str = TEST_SCHEMA, n_rows=N_ROWS_TEST_TABLES):
    """Populate missing tables in test schema"""
    # Detect
    tables_by_schema = {
        schema: [],
        test_schema: [],
    }
    for s in tables_by_schema:
        with get_db_connection(schema=s) as con:
            tables_by_schema[s] = list_tables(con, filter_temp_refresh_tables=True)
    missing_test_tables = list(set(tables_by_schema[schema]) - set(tables_by_schema[test_schema]))
    # Populate
    if missing_test_tables:
        _copy_over_tables(missing_test_tables, schema, test_schema, n_rows)


def _copy_over_tables(tables: List[str], schema= SCHEMA, test_schema=TEST_SCHEMA, n_rows=N_ROWS_TEST_TABLES):
    """Copy tables (n_rows of data) from schema into test schema, and create views."""
    # Copy tables
    with get_db_connection(schema='') as con:
        run_sql(con, f"""
                    DO $$ 
                    DECLARE
                        tables text[] := ARRAY{tables};
                        table_name text;
                    BEGIN
                        FOREACH table_name IN ARRAY tables
                        LOOP
                            EXECUTE format('
                                CREATE TABLE {test_schema}.%I AS
                                SELECT * FROM {schema}.%I LIMIT {n_rows}
                            ', table_name, table_name);
    
                            RAISE NOTICE 'Table %I created in {test_schema}', table_name;
                        END LOOP;
                    END $$;""")
    # Create views
    with get_db_connection(schema=test_schema) as con:
        views: List[str] = list_views()
        for view in views:
            statements: List[str] = get_ddl_statements(schema, view, return_type='flat')
            for statement in statements:
                    run_sql(con, statement)


if __name__ == '__main__':
    remake = True  # False by default to avoid accidents
    if remake:
        remake_test_schema()
