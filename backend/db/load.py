"""Load data into the database and create indexes and derived tables"""
from sqlalchemy.engine.base import Connection

from backend.db.config import CONFIG, DDL_PATH
from backend.db.utils import is_table_up_to_date, is_up_to_date, load_csv, run_sql, get_db_connection

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


# TODO: Given db refreshes now, address the following:
#  sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateTable) relation "csmi_idx2" already exists
# todo: skip_if_updated_within_hours: for now, set 1 key called `indexes_and_derived_tables_last_updated` in manage
def indexes_and_derived_tables(con: Connection, skip_if_updated_within_hours: int = None):
    """Create indexes and derived tables
    todo: (can do in ddl.sql): don't do anything if these tables exist & initialized"""
    print('INFO: Creating derived tables (e.g. `all_csets`) and indexes.')
    # with open(jinja_path, 'r') as file:
    #     template_str = file.read()
    # template_obj = Template(template_str)
    # # todo: hard-coded to 'prefixes' ok?
    # instantiated_str = template_obj.render({**kwargs, **{'prefixes': prefix_sparql_strings}}) if prefix_map \
    #     else template_obj.render(**kwargs)
    # with open(DDL_PATH, 'w') as f:
    #     f.write(instantiated_str)



    with open(DDL_PATH, 'r') as file:
        contents: str = file.read()
    # todo: change to run line-by-line using a delimiter (;\n\n? #--?)
    # commands: List[str] = [x + ';' for x in contents.split(';\n\n')]
    # for command in commands:
    #     try:
    #         run_sql(con, command)
    #     except (ProgrammingError, OperationalError):
    #         raise RuntimeError(f'Got an error executing the following statement:\n{command}')
    run_sql(con, contents)


def load(schema: str = SCHEMA, clobber=False, skip_if_updated_within_hours: int = None):
    """Load data into the database and create indexes and derived tables"""
    with get_db_connection() as con:
        # seed(con, schema, clobber, skip_if_updated_within_hours)
        indexes_and_derived_tables(con, skip_if_updated_within_hours)


if __name__ == '__main__':
    load()
