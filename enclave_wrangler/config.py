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
