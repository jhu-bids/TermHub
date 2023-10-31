import os
from dotenv import load_dotenv

APP_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.realpath(os.path.join(APP_ROOT, '..'))
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
ENV_FILE = os.path.join(ENV_DIR, '.env')
load_dotenv(ENV_FILE)
