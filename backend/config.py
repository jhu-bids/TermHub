import os
from dotenv import load_dotenv

APP_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.realpath(os.path.join(APP_ROOT, '..'))
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
ENV_FILE = os.path.join(ENV_DIR, '.env')
load_dotenv(ENV_FILE)

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
TERMHUB_CSETS_PATH = os.path.join(PROJECT_ROOT, 'termhub-csets')
DATASETS_PATH = os.path.join(TERMHUB_CSETS_PATH, 'datasets', 'prepped_files')
OBJECTS_PATH = os.path.join(TERMHUB_CSETS_PATH, 'objects')
DDL_JINJA_PATH_PATTERN = os.path.join(DB_DIR, 'ddl-*.jinja.sql')

CONFIG = {
    'server': os.getenv('TERMHUB_DB_SERVER'),
    'driver': os.getenv('TERMHUB_DB_DRIVER'),
    'host': os.getenv('TERMHUB_DB_HOST'),
    'user': os.getenv('TERMHUB_DB_USER'),
    'db': os.getenv('TERMHUB_DB_DB'),
    'schema': os.getenv('TERMHUB_DB_SCHEMA'),
    'pass': os.getenv('TERMHUB_DB_PASS'),
    'port': os.getenv('TERMHUB_DB_PORT'),
    'personal_access_token': os.getenv('GH_LIMITED_PERSONAL_ACCESS_TOKEN')
}
CONFIG_LOCAL = {
    'server': os.getenv('TERMHUB_DB_SERVER_LOCAL'),
    'driver': os.getenv('TERMHUB_DB_DRIVER_LOCAL'),
    'host': os.getenv('TERMHUB_DB_HOST_LOCAL'),
    'user': os.getenv('TERMHUB_DB_USER_LOCAL'),
    'db': os.getenv('TERMHUB_DB_DB_LOCAL'),
    'schema': os.getenv('TERMHUB_DB_SCHEMA_LOCAL'),
    'pass': os.getenv('TERMHUB_DB_PASS_LOCAL'),
    'port': os.getenv('TERMHUB_DB_PORT_LOCAL'),
    'personal_access_token': os.getenv('GH_LIMITED_PERSONAL_ACCESS_TOKEN')
}


def override_schema(schema: str):
    if CONFIG['schema']!= schema:
        print(f'Overriding {CONFIG["schema"]} schema to {schema}')
    else:
        CONFIG['schema'] = schema


def get_schema_name():
    return CONFIG['schema']
