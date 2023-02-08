"""Load data into the database and create indexes and derived tables"""
from typing import List

from jinja2 import Template
from psycopg2 import OperationalError, ProgrammingError
from sqlalchemy.engine.base import Connection

from backend.db.config import CONFIG, DDL_JINJA_PATH
from backend.db.utils import check_if_updated, current_datetime, is_table_up_to_date, load_csv, \
    run_sql, get_db_connection, update_db_status_var

DB = CONFIG["db"]
SCHEMA = CONFIG['schema']


def seed(con: Connection, schema: str = SCHEMA, clobber=False, skip_if_updated_within_hours: int = None):
    """Seed the database with some data"""
    replace_rule = 'do not replace' if not clobber else None
    dataset_tables_to_load = [
        'code_sets',
        'concept',
        'concept_ancestor',
        'concept_relationship',
        # 'concept_relationship_subsumes_only',
        'concept_set_container',
        'concept_set_counts_clamped',
        'concept_set_members',
        'concept_set_version_item',
        'deidentified_term_usage_by_domain_clamped',
    ]
    # table.lower(): because postgres won't recognize names with caps in them unless they are "quoted". should probably
    # do this with colnames also, but just using quotes in ddl
    object_tables_to_load = [x.lower() for x in [
        'researcher',
        'OMOPConceptSet',  # i to include RID
        'OMOPConceptSetContainer',  # to include RID
        # 'OMOPConceptSetVersionItem', only need this if we want the RID, but maybe don't need it
    ]]
    for table in dataset_tables_to_load:
        if skip_if_updated_within_hours and is_table_up_to_date(table, skip_if_updated_within_hours):
            print(f'INFO: Skipping upload of table "{table}" because it is up to date.')
            continue
        load_csv(con, table, replace_rule=replace_rule, schema=schema)
    for table in object_tables_to_load:
        if skip_if_updated_within_hours and is_table_up_to_date(table, skip_if_updated_within_hours):
            print(f'INFO: Skipping upload of table "{table}" because it is up to date.')
            continue
        load_csv(con, table, table_type='object', replace_rule=replace_rule, schema=schema)


def indexes_and_derived_tables(con: Connection, schema_name: str, skip_if_updated_within_hours: int = None):
    """Create indexes and derived tables"""
    # Determine and set up progress tracking
    last_completed_key = 'last_updated_indexes_and_derived_tables'
    last_successful_step_key = 'last_step_indexes_and_derived_tables'
    if skip_if_updated_within_hours and \
            check_if_updated(last_completed_key, skip_if_updated_within_hours):
        print(f'INFO: Skipping creation of indexes and derived tables because they are up to date.')
        return

    # Read DDL
    print('INFO: Creating derived tables (e.g. `all_csets`) and indexes.')
    with open(DDL_JINJA_PATH, 'r') as file:
        template_str = file.read()
    ddl = Template(template_str).render(schema=schema_name + '.')
    commands: List[str] = [x + ';' for x in ddl.split(';\n\n')]

    # Determine which steps still needed
    with get_db_connection(schema='') as con2:
        last_successful_step = run_sql(
            con2, f"SELECT value FROM manage WHERE key = '{last_successful_step_key}';").first()
    last_successful_step = int(last_successful_step[0]) if last_successful_step else None
    print('INFO: Creating derived tables (e.g. `all_csets`) and indexes.')
    if last_successful_step:
        print(f'INFO: Last successful command was {last_successful_step} of {len(commands)}. Continuing from there.')

    # Updates
    for index, command in enumerate(commands):
        step_num = index + 1
        if last_successful_step >= step_num:
            continue
        print(f'INFO: indexes_and_derived_tables: Running command {step_num} of {len(commands)}')
        try:
            run_sql(con, command)
        except (ProgrammingError, OperationalError, RuntimeError) as err:
            update_db_status_var(last_successful_step_key, str(step_num - 1))
            raise err

    update_db_status_var(last_successful_step_key, '0')
    update_db_status_var(last_completed_key, str(current_datetime()))


def load(schema: str = SCHEMA, clobber=False, skip_if_updated_within_hours: int = None, use_local_database=False):
    """Load data into the database and create indexes and derived tables"""
    with get_db_connection(use_local_database) as con:
        seed(con, schema, clobber, skip_if_updated_within_hours)
        indexes_and_derived_tables(con, schema, skip_if_updated_within_hours)


if __name__ == '__main__':
    load()
