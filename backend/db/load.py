"""Load data into the database and create indexes and derived tables"""
from sqlalchemy.engine.base import Connection

from backend.db.config import CONFIG, DDL_PATH
from backend.db.utils import load_csv, run_sql, get_db_connection

DB = CONFIG["db"]
SCHEMA = CONFIG['schema']


def seed(con: Connection, schema: str = SCHEMA, clobber=False):
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
    object_tables_to_load = [
        'researcher',
        'OMOPConceptSet',  # i to include RID
        'OMOPConceptSetContainer',  # to include RID
        # 'OMOPConceptSetVersionItem', only need this if we want the RID, but maybe don't need it
    ]
    for table in dataset_tables_to_load:
        load_csv(con, table, replace_rule=replace_rule, schema=schema)
    for table in object_tables_to_load:
        # use table.lower() because postgres won't recognize names with caps in them unless they
        #   are "quoted". should probably do this with colnames also, but just using quotes in ddl
        load_csv(con, table.lower(), table_type='object', replace_rule=replace_rule, schema=schema)


# TODO: Given db refreshes now, address the following:
#  sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable) relation "csmi_idx2" already exists
def indexes_and_derived_tables(con: Connection):
    """Create indexes and derived tables"""
    # TODO: run ddl
    #  a. use this delimiter thing. how delimit? ;\n\n? #--?
    #  b. sql alchemy: run sql string
    #  c. subprocess: psql termhub -i path/to/file
    # todo: (can do in ddl.sql): don't do anything if these tables exist & initialized
    print('INFO: Creating derived tables (e.g. `all_csets`) and indexes.')
    with open(DDL_PATH, 'r') as file:
        contents: str = file.read()
    run_sql(con, contents)
    # commands: List[str] = [x + ';' for x in contents.split(';\n\n')]
    # for command in commands:
    #     try:
    #         run_sql(con, command)
    #     except (ProgrammingError, OperationalError):
    #         raise RuntimeError(f'Got an error executing the following statement:\n{command}')


def load(schema: str = SCHEMA, clobber=False):
    """Load data into the database and create indexes and derived tables"""
    with get_db_connection() as con:
        seed(con, schema, clobber)
        indexes_and_derived_tables(con)


if __name__ == '__main__':
    load()
