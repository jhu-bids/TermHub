"""
Fully refresh the database with the latest data from the enclave API.
  here's what the run file is doing, i think, for datasets:
    ./venv/bin/python enclave_wrangler/datasets.py -f -o termhub-csets/datasets/downloads
"""
from datetime import datetime

from backend.db.load import load
from enclave_wrangler.datasets import run_favorites
from enclave_wrangler.objects_api import download_favorite_objects


def refresh_db():
    """Refresh the database"""
    temp_schema = 'n3c_' + datetime.now().strftime('%Y%m%d')
    # run_favorites(force_if_exists=True, single_group='cset')
    # download_favorite_objects(force_if_exists=True)
    load(schema=temp_schema, clobber=True)


if __name__ == '__main__':
    refresh_db()
