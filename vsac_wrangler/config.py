"""Config"""
import os
from dotenv import load_dotenv


APP_ROOT = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.join(APP_ROOT, '..')
ENV_DIR = os.path.join(PROJECT_ROOT, 'env')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
ENV_FILE = os.path.join(ENV_DIR, '.env')
CACHE_DIR = os.path.join(APP_ROOT, 'data', 'cache')
# Sheet of interest:
# - XLSX version: https://docs.google.com/spreadsheets/d/17hHiqc6GKWv9trcW-lRnv-MhZL8Swrx2/edit#gid=1335629675
# - https://docs.google.com/spreadsheets/d/1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18/edit#gid=405597125
SAMPLE_SPREADSHEET_ID = '1jzGrVELQz5L4B_-DqPflPIcpBaTfJOUTrVJT5nS_j18'
SAMPLE_RANGE_NAME = '{}!A1:AC'  # sheet name is passed by the CLI


load_dotenv(ENV_FILE)
config = {
    'vsac_api_key': os.getenv('VSAC_API_KEY')
}
