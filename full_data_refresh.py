from enclave_wrangler.datasets import download_favorite_datasets
from enclave_wrangler.objects_api import download_favorite_objects
from backend.db.initialize import initialize

"""
  here's what the run file is doing, i think, for datasets:
    ./venv/bin/python enclave_wrangler/datasets.py -f -o termhub-csets/datasets/downloads
"""

# run_favorites(force_download_if_exists=True, single_group='cset')
# download_favorite_objects(force_download_if_exists=True)

initialize(clobber=True)


