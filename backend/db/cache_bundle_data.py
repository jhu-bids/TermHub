"""Cache bundle data from N3C API before API access is removed.

Run this script while the N3C API is still accessible to cache bundle names
and codeset_ids for each bundle. The cached data will be used by the backend
endpoints after N3C API access is removed.

Usage:
    python -m backend.db.cache_bundle_data
"""
import json
import os
from pathlib import Path

from enclave_wrangler.objects_api import get_all_bundles, get_bundle_codeset_ids

CACHE_FILE = Path(__file__).parent / 'bundle_cache.json'


def cache_bundle_data():
    """Fetch and cache all bundle data from N3C API."""
    print("Fetching all bundles from N3C API...")
    all_bundles = get_all_bundles()

    bundle_data = {
        'bundle_names': [],
        'bundles': {}
    }

    for bundle in all_bundles['data']:
        display_name = bundle['properties']['displayName']
        tag_name = bundle['properties']['tagName']
        bundle_data['bundle_names'].append(display_name)

        print(f"Fetching codeset_ids for bundle: {display_name}")
        try:
            codeset_ids = get_bundle_codeset_ids(display_name)
            bundle_data['bundles'][display_name] = {
                'tag_name': tag_name,
                'codeset_ids': codeset_ids
            }
            print(f"  Found {len(codeset_ids)} codeset_ids")
        except Exception as e:
            print(f"  Error fetching codeset_ids: {e}")
            bundle_data['bundles'][display_name] = {
                'tag_name': tag_name,
                'codeset_ids': []
            }

    bundle_data['bundle_names'].sort()

    print(f"\nWriting cache to {CACHE_FILE}")
    with open(CACHE_FILE, 'w') as f:
        json.dump(bundle_data, f, indent=2)

    print(f"Cached {len(bundle_data['bundle_names'])} bundles")
    return bundle_data


def load_bundle_cache():
    """Load cached bundle data from file."""
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"Bundle cache not found at {CACHE_FILE}. "
            "Run cache_bundle_data() while N3C API is still accessible."
        )

    with open(CACHE_FILE, 'r') as f:
        return json.load(f)


def get_cached_bundle_names():
    """Get list of bundle names from cache."""
    cache = load_bundle_cache()
    return cache['bundle_names']


def get_cached_bundle_codeset_ids(bundle_name):
    """Get codeset_ids for a bundle from cache."""
    cache = load_bundle_cache()
    bundle = cache['bundles'].get(bundle_name)
    if bundle is None:
        return []
    return bundle['codeset_ids']


if __name__ == '__main__':
    cache_bundle_data()
