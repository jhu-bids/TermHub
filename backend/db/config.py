"""Configuration for TermHub database"""
from typing import Dict, List

from backend.config import CONFIG, CONFIG_LOCAL


def invert_list_dict(d1: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Invert a dictionary with lists as values"""
    if any(not isinstance(value, list) for value in d1.values()):
        raise ValueError('Dictionary values must be lists')
    d2 = {}
    for key, values in d1.items():
        for value in values:
            if value in d2:
                d2[value].append(key)
            else:
                d2[value] = [key]
    return d2


def recursify_key_in_list_dict(d1: Dict[str, List[str]], key: str) -> Dict:
    """Given a dictionary with keys and values that may or may not be keys in the dictionary, and given a specific key,
    recursively go through and build a dictionary for that key of all of the recursive key value mappings."""
    if key in d1:
        inner_map = {}
        for value in d1[key]:
            inner_map[value] = recursify_key_in_list_dict(d1, value)
        # return {key: inner_map}
        return inner_map
    else:
        return {}


def recursify_list_dict(d1: Dict[str, List[str]]) -> Dict[str, Dict]:
    """Given a dictionary with keys and values that may or may not be keys in the dictionary, recursively go through and
     build a dictionary of each key as it maps to its values."""
    d2 = {}
    for key in d1.keys():
        d2[key] = recursify_key_in_list_dict(d1, key)
    return d2

def get_pg_connect_url(local=False):
    """Get URL to connect to the database server"""
    config = CONFIG_LOCAL if local else CONFIG
    return f'{config["server"]}+{config["driver"]}://' \
           f'{config["user"]}:{config["pass"]}@{config["host"]}:{config["port"]}' \
           f'/{config["db"]}'


# https://stackoverflow.com/a/49927846/1368860
# def connect(conn_config_file = 'Commons/config/conn_commons.json'):
#     with open(conn_config_file) as config_file:
#         conn_config = json.load(config_file)
#
#     schema = conn_config['schema']
#     conn = psycopg2.connect(
#         dbname=conn_config['dbname'],
#         user=conn_config['user'],
#         host=conn_config['host'],
#         password=conn_config['password'],
#         port=conn_config['port'],
#         options=f'-c search_path={schema}',
#     )
#     return conn
# CONFIG['pgparams'] = {
#     'dbname': CONFIG['dbname'],
#     'user': CONFIG['user'],
#     'host': CONFIG['host'],
#     'password': CONFIG['password'],
#     'port': CONFIG['port'],
#     'options': f'-c search_path={schema}',
# }

BRAND_NEW_DB_URL = \
    f'{CONFIG["server"]}+{CONFIG["driver"]}://{CONFIG["user"]}:{CONFIG["pass"]}@{CONFIG["host"]}:{CONFIG["port"]}'
# todo: @Siggie: can remove ?charset=utf8mb4 if we don't need. It was there when I pulled example from sqlalchemy. But
#  it throws error when using postgres.
if CONFIG["server"] == 'mysql':
    BRAND_NEW_DB_URL = BRAND_NEW_DB_URL + '?charset=utf8mb4'
DB_URL = BRAND_NEW_DB_URL.replace(f'{CONFIG["port"]}', f'{CONFIG["port"]}/{CONFIG["db"]}')
REFRESH_JOB_MAX_HRS = 6  # see is_refresh_active() for documentation on this var
PG_DATATYPES_BY_GROUP = {
    'numeric': ['integer', 'bigint', 'smallint', 'real', 'double precision', 'numeric'],
    'string': ['text', 'character', 'character varying'],
    'datetime': ['timestamp with time zone', 'timestamp without time zone', 'time with time zone',
                 'time without time zone']
}
# Table/View configuration: for n3c schema
CORE_CSET_TABLES = ['code_sets', 'concept_set_container', 'concept_set_version_item', 'concept_set_members']
# STANDALONE_TABLES & DERIVED_TABLE_DEPENDENCY_MAP
#  - 100% of tables in the main schema, e.g. n3c, should be listed somewhere in
# STANDALONE_TABLES: Not derived from any other table, nor used to derive any other table/view. Used for QC testing.
STANDALONE_TABLES = [
    'concept_set_json',
    'junk',
    'relationship',
    'session_concept',
    'sessions',
    'test',
    'code_sets_audit',
    'vocabulary',
    'domain',
]
# DERIVED_TABLE_DEPENDENCY_MAP: Shows which tables are needed to create a derived table. Generally the idea is that when
#  the dependency tables are updated, the dependent table also needs to be updated. But some tables in here have
#  dependencies but do not meet that use case. for example, 'concept_set_members_with_dups' depends on
#  'concept_set_members', but that table is temporary.
# - Last updated: 2024/04/07
# todo: are the 'module names' part of the DDL file names the same as the keys in this dictionary? If so, write that
#  down here as a comment. Could be useful for dynamically selecting the DDL files.
DERIVED_TABLE_DEPENDENCY_MAP: Dict[str, List[str]] = {
    # Dependencies figured out
    # - tables
    # all_csets: omopconceptset is all lowercase in DB but referred to as OMOPConceptSet in DDL and enclave object API
    'all_csets': [
        # - These two are dependencies on temp table 'cset_term_usage_rec_counts' which is created & deleted during
        #   all_csets DDL runtime
        'concept_set_members', 'concepts_with_counts',
        # - These rest are just regular dependencies on all_csets
        'code_sets', 'omopconceptset', 'concept_set_container', 'omopconceptsetcontainer',
        'concept_set_counts_clamped',
        'codeset_counts', 'researcher'
    ],
    'codeset_counts': ['members_items_summary'],
    'concept_ancestor_plus': ['concept_ancestor', 'concepts_with_counts'],
    'concept_graph': ['concept_ancestor'],
    'concept_relationship_plus': ['concept_relationship', 'concepts_with_counts'],
    'concepts_with_counts': ['concepts_with_counts_ungrouped'],
    'concepts_with_counts_ungrouped': ['concept', 'deidentified_term_usage_by_domain_clamped'],
    'cset_members_items': ['concept_set_members', 'concept_set_version_item'],
    'members_items_summary': ['cset_members_items'],

    # - views
    # 'csets_to_ignore': ['all_csets'],
    'all_csets_view': ['all_csets'],

    # Unfinished / unsure
    # - unsure what to do with these. they probably aren't derived either
    # 'junk': [],
    # 'omopconceptset': [],
    # 'omopconceptsetcontainer': [],

    # Non-derived tables
    # - core cset tables
    # 'code_sets': [],
    # 'concept_set_version_item': [],
    # 'concept_set_container': [],
    # 'concept_set_members': [],
    # # - vocab
    # 'concept': [],
    # 'concept_ancestor': [],
    # 'relationship': [],
    # 'concept_relationship': [],
    # # - counts
    # 'deidentified_term_usage_by_domain_clamped': [],
    # 'concept_set_counts_clamped': [],
    # # - objects
    # 'researcher': [],

    # Public schema
    # todo? Probably not a use case for adding such tables here. As of 2024/04/07, public tables/views are:
    # - dependent
    # apijoin
    # apiruns_plus
    # apirruns_grouped
    # - independent
    # api_runs
    # codeset_comparison
    # counts
    # counts_runs
    # fetch_audit
    # ip_info
    # manage

}
# DIRECT_DEPENDENT_TABLES: Keys are tables. Values are tables that depend on the table in the key. That is to say, when
# the table in the key is updated, the tables in the values under that key also need to be updated. Inversion of
#  DERIVED_TABLE_DEPENDENCY_MAP. If nothing depends on a table, it  will not appear in the keys.
DIRECT_DEPENDENT_TABLE_MAP = invert_list_dict(DERIVED_TABLE_DEPENDENCY_MAP)
# RECURSIVE_DEPENDENT_TABLE_MAP: Hierarchy of each table and all of the tables that depend on it. If nothing depends on
# a table, it  will not appear in the keys.
RECURSIVE_DEPENDENT_TABLE_MAP: Dict[str, Dict] = recursify_list_dict(DIRECT_DEPENDENT_TABLE_MAP)
