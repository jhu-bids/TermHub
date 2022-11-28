"""Configuration for TermHub database"""
import os
from dotenv import load_dotenv

DB_DIR = os.path.dirname(os.path.realpath(__file__))
BACKEND_DIR = os.path.join(DB_DIR, '..')
PROJECT_ROOT = os.path.join(BACKEND_DIR, '..')
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
ENV_FILE = os.path.join(ENV_DIR, '.env')
DDL_PATH = os.path.join(DB_DIR, 'ddl.sql')
load_dotenv(ENV_FILE)
CONFIG = {
    'host': os.getenv('TERMHUB_DB_HOST'),
    'user': os.getenv('TERMHUB_DB_USER'),
    'db': os.getenv('TERMHUB_DB_DB'),
    'pass': os.getenv('TERMHUB_DB_PASS'),
    'port': os.getenv('TERMHUB_DB_PORT'),
}
DB_URL = f'mysql+pymysql://{CONFIG["user"]}:{CONFIG["pass"]}@{CONFIG["host"]}:{CONFIG["port"]}/{CONFIG["db"]}?charset=utf8mb4'
BRAND_NEW_DB_URL = f'mysql+pymysql://{CONFIG["user"]}:{CONFIG["pass"]}@{CONFIG["host"]}:{CONFIG["port"]}?charset=utf8mb4'
