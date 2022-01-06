"""Config"""
import os
from dotenv import load_dotenv


APP_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.join(APP_ROOT, '..')
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
ENV_FILE = os.path.join(ENV_DIR, '.env')
CACHE_DIR = os.path.join(APP_ROOT, 'data', 'cache')

load_dotenv(ENV_FILE)
config = {
    'vsac_api_key': os.getenv('VSAC_API_KEY')
}
