"""Config"""
import os
from collections import OrderedDict
from backend.config import PROJECT_ROOT, ENV_FILE

TERMHUB_VERSION = "0.0.1"


TERMHUB_CSETS_DIR = os.path.join(PROJECT_ROOT, 'termhub-csets')
UPLOADS_DIR = os.path.join(TERMHUB_CSETS_DIR, 'datasets', 'uploads')
OUTDIR_OBJECTS = os.path.join(TERMHUB_CSETS_DIR, 'objects')
OUTDIR_DATASETS = os.path.join(TERMHUB_CSETS_DIR, 'datasets')
OUTDIR_CSET_JSON = os.path.join(TERMHUB_CSETS_DIR, 'cset_json')
OUTDIR_DATASETS_DOWNLOADED = os.path.join(OUTDIR_DATASETS, 'downloads')
OUTDIR_DATASETS_TRANSFORMED = os.path.join(OUTDIR_DATASETS, 'prepped_files')
CSET_UPLOAD_REGISTRY_PATH = os.path.join(UPLOADS_DIR, 'cset_upload_registry.csv')

# CSET_VERSION_MIN_ID: For concept set versions we are uploading, we can assign our own ID. Must be higher than this num
CSET_VERSION_MIN_ID = 1000000000
ENCLAVE_PROJECT_NAME = 'RP-4A9E27'
PALANTIR_ENCLAVE_USER_ID_1 = 'a39723f3-dc9c-48ce-90ff-06891c29114f'
MOFFIT_PREFIX = 'Simplified autoimmune disease'
MOFFIT_SOURCE_URL = 'https://docs.google.com/spreadsheets/d/1tHHHeMtzX0SA85gbH8Mvw2E0cxH-x1ii/edit#gid=1762989244'
MOFFIT_SOURCE_ID_TYPE = 'moffit'
VALIDATE_FIRST = False  # if True, will /validate before doing /apply, and return validation error if any.

RESEARCHER_COLS = ['container_created_by', 'codeset_created_by', 'assigned_sme', 'reviewed_by', 'n3c_reviewer',
                   'assigned_informatician']

config = {
    'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN': os.getenv('PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN', '').replace('\r', ''),
    'OTHER_TOKEN': os.getenv('OTHER_TOKEN', '').replace('\r', ''),
    # this caused an error on the frontend. for some reason resolving to '7ccd429394d3' instead of 'unite.nih.gov'
    # 'HOSTNAME': os.getenv('HOSTNAME', 'unite.nih.gov').replace('\r', ''),
    'HOSTNAME': 'unite.nih.gov',
    'ONTOLOGY_RID': os.getenv('ONTOLOGY_RID', 'ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000').replace('\r', ''),
    'SERVICE_USER_ID': os.getenv('SERVICE_USER_ID', '').replace('\r', ''),
    'DIH_PROJ_ID': os.getenv('DIH_PROJ_ID', '').replace('\r', ''),
}
# todo: as of 2022/10/20, it looks like some functionality/endpoints need PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN,
#  and others need OTHER_TOKEN, but it's not entirely clear where each are required yet. when that's figured out, can
#  move this `raise EnvironmentError` check further down to where the env var is actually needed.
necessary_env_vars = []
# necessary_env_vars = ['OTHER_TOKEN', 'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']
missing_env_vars = [x for x in necessary_env_vars if not config[x]]
if missing_env_vars:
    cause_msg = f'The file {ENV_FILE} is missing. This file is necessary and must contain these ' \
                f'environmental variables in order to connect to the enclave.' if not os.path.exists(ENV_FILE) else \
                f'Please make update {ENV_FILE} to include these variables.'
    raise EnvironmentError(
        f'Attempted to load config, but wasn\'t able to load the following environmental variables: '
        f'{", ".join(missing_env_vars)}\n'
        f'{cause_msg}')

OBJECT_REGISTRY = [
    'researcher',
    # 'research-project',

    # todo: 2023/03/20 Joe: Do we need this error message here? Are we looking to fetch CodeSystemConceptSetVersionExpressionItem?
    # 'CodeSystemConceptSetVersionExpressionItem',
    # {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'ObjectsExceededLimit', 'errorInstanceId':
    # '693c5f19-df1f-487e-afb9-ea6c6adb8996', 'parameters': {}}

    #     these are being downloaded as datasets, not sure why they're listed here. commenting out
    #     'OMOPConcept',
    #     'OMOPConceptSet',
    #     'OMOPConceptSetContainer',
    #     'OmopConceptSetVersionItem',
]
# todo: refactor/rename: This is more than just favorite datasets now. This is a data model configuration. Ideally, all
#  tables should have an entry here, and we should add a key 'favorited_dataset' (bool) under each.
#  For example, models.py PKEYS still has some of this primary key info.
# todo: All indexes should be listed here, and initialize/refresh refactored such that indexex get created by generating
#  SQL from here, rather than reading from the DDL files.
# Ordered because of transformation dependencies
DATASET_REGISTRY = OrderedDict({
    # apparently concept_set_container has a lot more rows than concept_set_container_edited. not sure
    #   why we were getting edited or why they're different
    'concept_set_container': {
        'name': 'concept_set_container',
        #   https://unite.nih.gov/workspace/data-integration/dataset/preview/ri.foundry.main.dataset.c9932f52-8b27-4e7b-bdb1-eec79e142182/master
        #   /N3C Export Area/Concept Set Ontology/Concept Set Ontology/hubble_base/concept_set_container
        'rid': 'ri.foundry.main.dataset.c9932f52-8b27-4e7b-bdb1-eec79e142182',
        'sort_idx': ['concept_set_name'],
        'converters': {'archived': lambda x: True if x == 'True' else False},  # this makes it a bool field
        'dataset_groups': ['cset'],
        'primary_key': 'concept_set_id'
    },
    # 'concept_set_container_edited': {
    #     'name': 'concept_set_container_edited',
    #     'rid': 'ri.foundry.main.dataset.8cb458de-6937-4f50-8ef5-2b345382dbd4',
    #     'sort_idx': ['concept_set_name'],
    #     'converters': {'archived': lambda x: True if x == 'True' else False},  # this makes it a bool field
    # },
    'code_sets': {  # transform depends on: concept_set_container_edited untransformed
        'name': 'code_sets',
        'rid': 'ri.foundry.main.dataset.7104f18e-b37c-419b-9755-a732bfa33b03',
        'sort_idx': ['codeset_id'],
        'dataset_groups': ['cset'],
        'primary_key': 'codeset_id'
    },
    'concept_set_members': {
        'name': 'concept_set_members',
        'rid': 'ri.foundry.main.dataset.e670c5ad-42ca-46a2-ae55-e917e3e161b6',
        'sort_idx': ['codeset_id', 'concept_id'],
        'dataset_groups': ['cset'],
        'primary_key': ['codeset_id', 'concept_id']
    },
    'concept': {  # transform depends on: concept_set_members transform
        'name': 'concept',
        'rid': 'ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772',
        'sort_idx': ['concept_id'],
        'dataset_groups': ['vocab'],
        'index_on': ['concept_id', 'concept_code'],  # todo: not currently used, but could do this instead of ddl.sql
        'primary_key': 'concept_id'
    },
    'concept_ancestor': {  # transform depends on: concept_set_members transform
        'name': 'concept_ancestor',
        'rid': 'ri.foundry.main.dataset.c5e0521a-147e-4608-b71e-8f53bcdbe03c',
        'sort_idx': ['ancestor_concept_id', 'descendant_concept_id'],
        'dataset_groups': ['vocab']
    },
    'concept_relationship': {  # transform depends on: concept_set_members transform
        'name': 'concept_relationship',
        'rid': 'ri.foundry.main.dataset.0469a283-692e-4654-bb2e-26922aff9d71',
        'sort_idx': ['concept_id_1', 'concept_id_2'],
        'dataset_groups': ['vocab']
    },
    'concept_set_version_item': {
        # actually, this one is missing stuff. using concept_set_version_item_rv instead
        #   but leaving the inaccurate name so I don't have to change it all over the code
        'name': 'concept_set_version_item',
        'rid': 'ri.foundry.main.dataset.f2355e2f-51b6-4ae1-ae80-7e869c1933ac',
        # was: 'rid': 'ri.foundry.main.dataset.1323fff5-7c7b-4915-bcde-4d5ba882c993',
        'sort_idx': ['codeset_id', 'concept_id'],
        'dataset_groups': ['cset'],
        'primary_key': 'item_id'  # todo: change to codeset_id,concept_id?
    },
    'concept_set_counts_clamped': { # gets downloaded as csv without column names, not parquet
        'name': 'concept_set_counts_clamped',
        'rid': 'ri.foundry.main.dataset.f945409a-37f1-402f-a840-29b6bd675cb0',
        'column_names': ["codeset_id", "approx_distinct_person_count", "approx_total_record_count"],
        'sort_idx': ['codeset_id'],
        'dataset_groups': ['counts']
    },
    'deidentified_term_usage_by_domain_clamped': { # gets downloaded as csv without column names, not parquet
        'name': 'deidentified_term_usage_by_domain_clamped',
        'rid': 'ri.foundry.main.dataset.e393f03a-00d0-4071-802c-ff20e543ce01',
        'column_names': ["concept_id", "domain", "total_count", "distinct_person_count"],
        'sort_idx': ['concept_id', 'domain'],
        'dataset_groups': ['counts']
    },
    'relationship': { # gets downloaded as csv without column names, not parquet
        'name': 'relationship',
        'rid': 'ri.foundry.main.dataset.478c12f2-2410-4880-859e-c2267bc28779',
        'column_names': ["relationship_id", "relationship_name", "is_hierarchical", "defines_ancestry",
                            "reverse_relationship_id", "relationship_concept_id"],
        'sort_idx': ['relationship_name'],
        'dataset_groups': ['vocab']
    },
    'vocabulary': {
        'name': 'vocabulary',
        'rid': 'ri.foundry.main.dataset.0e1acd60-6eeb-49e1-9189-1b8a6221ac29',
        'column_names': ["vocabulary_id", "vocabulary_name", "vocabulary_reference", "vocabulary_version", "vocabulary_concept_id"],
        'sort_idx': ['vocabulary_id'],
        'dataset_groups': ['vocab']
    },
    'domain': {
        'name': 'domain',
        'rid': 'ri.foundry.main.dataset.e1f7eefb-4730-43cf-9bad-42b0c3803740',
        'column_names': ["domain_id", "domain_name", "domain_concept_id"],
        'sort_idx': ['domain_id'],
        'dataset_groups': ['vocab']
    },
    # not downloadable -- yet
    # 'safe_harbor_term_usage': {
    #     'name': 'safe_harbor_term_usage',
    #     'enclave_path': '/UNITE/Concept Term Usage Analysis/datasets/safe_harbor_term_usage',
    #     'rid': 'ri.foundry.main.dataset.c37927d3-db40-4c54-bea5-036b76c858c9',
    # },
    # '': {
    #     'name': '',
    #     'rid': '',
    # },
})
DATASET_REGISTRY_RID_NAME_MAP = {
    v['rid']: k
    for k, v in DATASET_REGISTRY.items()
}
DATASET_GROUPS_CONFIG = {
    'vocab': {
        'last_updated_termhub_var': 'last_refreshed_vocab_tables',
        'last_updated_enclave_representative_table': 'concept',
        'dataset_group': 'vocab',
        'tables': [x['name'] for x in DATASET_REGISTRY.values() if 'vocab' in x['dataset_groups']]
    },
    'counts': {
        'last_updated_termhub_var': 'last_refreshed_counts_tables',
        'last_updated_enclave_representative_table': 'concept_set_counts_clamped',
        'dataset_group': 'counts',
        'tables': [x['name'] for x in DATASET_REGISTRY.values() if 'counts' in x['dataset_groups']]
    }
}
