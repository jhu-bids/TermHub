"""Configuration for TermHub database"""
import os
from dotenv import load_dotenv

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
ENV_FILE = os.path.join(ENV_DIR, '.env')
TERMHUB_CSETS_PATH = os.path.join(PROJECT_ROOT, 'termhub-csets')
DATASETS_PATH = os.path.join(TERMHUB_CSETS_PATH, 'datasets', 'prepped_files')
OBJECTS_PATH = os.path.join(TERMHUB_CSETS_PATH, 'objects')
DDL_JINJA_PATH = os.path.join(DB_DIR, 'ddl.jinja.sql')
load_dotenv(ENV_FILE)
CONFIG = {
    'server': os.getenv('TERMHUB_DB_SERVER'),
    'driver': os.getenv('TERMHUB_DB_DRIVER'),
    'host': os.getenv('TERMHUB_DB_HOST'),
    'user': os.getenv('TERMHUB_DB_USER'),
    'db': os.getenv('TERMHUB_DB_DB'),
    'schema': os.getenv('TERMHUB_DB_SCHEMA'),
    'pass': os.getenv('TERMHUB_DB_PASS'),
    'port': os.getenv('TERMHUB_DB_PORT'),
}

def get_pg_connect_url():
    return  f'{CONFIG["server"]}+{CONFIG["driver"]}://' \
            f'{CONFIG["user"]}:{CONFIG["pass"]}@{CONFIG["host"]}:{CONFIG["port"]}' \
            f'/{CONFIG["db"]}'


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
