"""Config"""
import os
from dotenv import load_dotenv


APP_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.join(APP_ROOT, '..')
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
ENV_FILE = os.path.join(ENV_DIR, '.env')
TERMHUB_CSETS_DIR = os.path.join(PROJECT_ROOT, 'termhub-csets')


load_dotenv(ENV_FILE)
config = {
    'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN': os.getenv('PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN'),
    'OTHER_TOKEN': os.getenv('OTHER_TOKEN'),
    'HOSTNAME': os.getenv('HOSTNAME', 'unite.nih.gov'),
    'ONTOLOGY_RID': os.getenv('ONTOLOGY_RID', 'ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000'),
}

FAVORITE_DATASETS = {
    'concept': {
        'name': 'concept',
        'rid': 'ri.foundry.main.dataset.5cb3c4a3-327a-47bf-a8bf-daf0cafe6772',
    },
    'concept_relationship': {
        'name': 'concept_relationship',
        'rid': 'ri.foundry.main.dataset.0469a283-692e-4654-bb2e-26922aff9d71'
    },
    'concept_set_container_edited': {
        'name': 'concept_set_container_edited',
        'rid': 'ri.foundry.main.dataset.8cb458de-6937-4f50-8ef5-2b345382dbd4',
    },
    'code_sets': {
        'name': 'code_sets',
        'rid': 'ri.foundry.main.dataset.7104f18e-b37c-419b-9755-a732bfa33b03',
    },
    'concept_set_version_item': {
        'name': 'concept_set_version_item',
        'rid': 'ri.foundry.main.dataset.1323fff5-7c7b-4915-bcde-4d5ba882c993',
    },
    'concept_set_members': {
        'name': 'concept_set_members',
        'rid': 'ri.foundry.main.dataset.e670c5ad-42ca-46a2-ae55-e917e3e161b6',
    },
    # '': {
    #     'name': '',
    #     'rid': '',
    # },
}
