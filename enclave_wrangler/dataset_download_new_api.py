#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download."""
import json
import os
from argparse import ArgumentParser
from datetime import datetime
from typing import List, Dict, Callable

import pandas as pd
from typeguard import typechecked

import requests
# import pyarrow as pa
# import asyncio

from enclave_wrangler.config import config
# from enclave_wrangler.utils import log_debug_info


HEADERS = {
    "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    "Content-type": "application/json",
    #'content-type': 'application/json'
}
DEBUG = False
# TARGET_CSV_DIR='data/datasets/'


class EnclaveClient:
    """REST client for N3C data enclave"""

    def __init__(self):
        self.headers = HEADERS
        self.debug = DEBUG
        self.base_url = f'https://{config["HOSTNAME"]}'
        self.ontology_rid = config['ONTOLOGY_RID']
        self.cache_dir = config['CACHE_DIR']

    @typechecked
    def obj_types(self) -> List[Dict]:
        """Gets object types.
        API docs: https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/

        TODO: @Siggie: Here's what I found that looked interesting:
         ConceptRelationship, ConceptSetBundleItem, ConceptSetTag, ConceptSetVersionChangeAcknowledgement,
         ConceptSuccessorRelationship, ConceptUsageCounts, CsetVersionInfo, CodeSystemConceptSetVersionExpressionItem,
         OMOPConcept, OMOPConceptAncestorRelationship, OMOPConceptChangeConnectors, OMOPConceptSet,
         OMOPConceptSetContainer, OMOPConceptSetReview, OmopConceptChange, OmopConceptDomain, OmopConceptSetVersionItem,
        """
        url = f'{self.base_url}/api/v1/ontologies/{self.ontology_rid}/objectTypes'
        response = requests.get(url, headers=self.headers)
        response_json = response.json()['data']  # always returns everything in nested 'data' key
        # types = pd.DataFrame(data=response_json)
        # types = sorted([x['apiName'] for x in response_json])
        return response_json['data']

    # TODO: Implement this func to get all concept sets
    #  - handle pagination. I think get 1k at a time
    # TODO: after: for each set, get all concepts.
    # TODO: Look at Siggie's frontend/ code to see how OMOPConceptSet etc are being called/used
    # TODO: Need to find the right object_type, then write a wrapper func around this to get concept sets
    #  - To Try: CodeSystemConceptSetVersionExpressionItem, OMOPConcept, OMOPConceptSet, OMOPConceptSetContainer,
    #    OmopConceptSetVersionItem
    def objects(self, object_type) -> pd.DataFrame:
        """Get objects
        Docs: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
        https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/"""
        # Request
        results: List[Dict] = []
        url_base = f'{self.base_url}/api/v1/ontologies/{self.ontology_rid}/objects/{object_type}'
        url = url_base
        while True:
            response = requests.get(url, headers=self.headers)
            response_json = response.json()
            if response.status_code >= 400:  # err
                break
            results += response_json['data']
            if 'nextPageToken' not in response_json or not response_json['nextPageToken']:
                break
            url = url_base + '?pageToken=' + response_json["nextPageToken"]

        # Parse
        # Get rid of nested 'properties' key, and add 'rid' in with the other fields
        if results:
            results = [{**x['properties'], **{'rid': x['rid']}} for x in results]
            df = pd.DataFrame(results).fillna('')

            # Cache
            # TODO: temporary cache code until decide where/how to write these
            cache_dir = os.path.join(self.cache_dir, 'objects', object_type)
            date_str = str(datetime.now()).replace(':', '-')
            cache_path = os.path.join(cache_dir, date_str + '.csv')
            if not os.path.exists(cache_dir):
                os.mkdir(cache_dir)
            df.to_csv(cache_path, index=False)
            # todo: Would be good to have all enclave_wrangler requests basically wrap around python `requests` and also
            #  ...utilize this error reporting, if they are saving to disk.
            if response.status_code >= 400:
                error_report: Dict = {'request': url, 'response': response_json}
                with open(os.path.join(cache_dir, f'{date_str} - error {response.status_code}.json'), 'w') as file:
                    json.dump(error_report, file)

            return df

    def link_types(self) -> List[Dict]:
        """Get link types
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
        "https://unite.nih.gov/ontology-metadata/api/ontology/linkTypesForObjectTypes" --data '{
            "objectTypeVersions": {
                "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                "00000001-9834-2acf-8327-ecb491e69b5c"
            }
        }' | jq '..|objects|.apiName//empty'
        """
        # TODO: @Siggie I tried using the above curl in Python but I got this (- Joe 2022/08/21):
        #  {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'Conjure:UnsupportedMediaType', 'errorInstanceId':
        #  '7976c277-8187-4a5a-91b9-2e8bd1c9934c', 'parameters': {}}
        #  @jflack: There was an extra backslash in the curl cmd. see #96
        data = {
            "objectTypeVersions": {
                "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                    "00000001-9834-2acf-8327-ecb491e69b5c"
            }
        }
        url = f'{self.base_url}/ontology-metadata/api/ontology/linkTypesForObjectTypes'
        response = requests.post(url, headers=self.headers, data=data)
        response_json = response.json()
        return response_json


def run(request_types: List[str]) -> Dict[str, Dict]:
    """Run"""
    client = EnclaveClient()
    request_funcs: Dict[str, Callable] = {
        'objects': client.objects,
        'object_types': client.obj_types,
        'link_types': client.link_types,
    }
    results = {}
    for req in request_types:
        results[req] = request_funcs[req]()
        # if req == 'object_types':
        #     print('\n'.join([t['apiName'] for t in results[req]['types']]))
    return results


# TODO: @Siggie: Temp; just want to look at all the data before deciding what to do w/ it
def cache_objects_of_interest():
    """Cache objects of interest"""
    of_interest = [
        # 'CodeSystemConceptSetVersionExpressionItem',
        # {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'ObjectsExceededLimit', 'errorInstanceId':
        # '693c5f19-df1f-487e-afb9-ea6c6adb8996', 'parameters': {}}

        'OMOPConcept',
        'OMOPConceptSet',
        'OMOPConceptSetContainer',
        'OmopConceptSetVersionItem'
    ]
    client = EnclaveClient()
    for o in of_interest:
        # Only runs if nothing exists in cache
        if not os.path.exists(os.path.join(config['CACHE_DIR'], 'objects', o)):
            client.objects(o)


def cli():
    """Command line interface for package."""
    package_description = 'Tool for working w/ the Palantir Foundry enclave API. ' \
                          'This part is for downloading enclave datasets.'
    parser = ArgumentParser(description=package_description)

    # parser.add_argument(
    #     '-a', '--auth_token_env_var',
    #     default='PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN',
    #     help='Name of the environment variable holding the auth token you want to use')
    # todo: 'objects' alone doesn't make sense because requires param `object_type`
    parser.add_argument(
        '-r', '--request-types',
        nargs='+', default=['object_types', 'objects', 'link_types'],
        help='Types of requests to make to the API.')
    parser.add_argument(
        '-c', '--cache-objects-of-interest',
        action='store_true', help='Cache objects as CSV.')
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    if kwargs_dict['cache_objects_of_interest']:
        cache_objects_of_interest()
    else:
        del kwargs_dict['cache_objects_of_interest']
        run(**kwargs_dict)


if __name__ == '__main__':
    cli()
