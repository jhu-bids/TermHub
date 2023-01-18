#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dataset download.

Resources
- https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/

TODO's
 1. Consider refactor: Python -> Bash (curl + JQ)
 2. Are the tables in 'datasets' isomorphic w/ 'objects'? e.g. object OmopConceptSetVersionItem == table
 concept_set_version_item_rv_edited_mapped.
"""
import json
import os
from argparse import ArgumentParser
from typing import List, Dict, Callable, Union

import pandas as pd
from requests import Response
from typeguard import typechecked

import requests
# import pyarrow as pa
# import asyncio

from enclave_wrangler.config import FAVORITE_OBJECTS, OUTDIR_OBJECTS, config, TERMHUB_CSETS_DIR
from enclave_wrangler.utils import make_objects_request, enclave_post

# from enclave_wrangler.utils import log_debug_info


HEADERS = {
    # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
    "authorization": f"Bearer {config['OTHER_TOKEN']}",
    "Content-type": "application/json",
    #'content-type': 'application/json'
}
DEBUG = False


class EnclaveClient:
    """REST client for N3C data enclave"""

    def __init__(self):
        self.headers = HEADERS
        self.debug = DEBUG
        self.base_url = f'https://{config["HOSTNAME"]}'
        self.ontology_rid = config['ONTOLOGY_RID']
        self.outdir_root = TERMHUB_CSETS_DIR

    @typechecked
    def get_obj_types(self) -> List[Dict]:
        """Gets object types.
        API docs: https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/

        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" "https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/objectTypes" | jq

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

    def _handle_paginated_request(self, first_page_url: str) -> (List[Dict], Response):
        """Handles a request that has a nextPageToken, automatically fetching all pages and combining the data"""
        url = first_page_url
        results: List[Dict] = []
        while True:
            response = requests.get(url, headers=self.headers)
            response_json = response.json()
            if response.status_code >= 400:  # err
                break
            results += response_json['data']
            if 'nextPageToken' not in response_json or not response_json['nextPageToken']:
                break
            url = first_page_url + '?pageToken=' + response_json["nextPageToken"]
        return results, response


    # todo?: Need to find the right object_type, then write a wrapper func around this to get concept sets
    #  - To Try: CodeSystemConceptSetVersionExpressionItem, OMOPConcept, OMOPConceptSet, OMOPConceptSetContainer,
    #    OmopConceptSetVersionItem
    def get_objects_by_type(
        self, object_type: str, save_csv=True, save_json=True, outdir: str = None) -> pd.DataFrame:
        """Get objects
        Docs: https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
        https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/"""
        # Request
        first_page_url = f'{self.base_url}/api/v1/ontologies/{self.ontology_rid}/objects/{object_type}'
        results, last_response = self._handle_paginated_request(first_page_url)

        # Parse
        # Get rid of nested 'properties' key, and add 'rid' in with the other fields
        df = pd.DataFrame()
        if results:
            results = [{**x['properties'], **{'rid': x['rid']}} for x in results]
            df = pd.DataFrame(results).fillna('')

        # Save
        outdir = outdir if outdir else os.path.join(OUTDIR_OBJECTS, object_type)
        outpath = os.path.join(outdir, 'latest.csv')
        if not os.path.exists(outdir) and (save_json or save_csv):
            os.mkdir(outdir)
        # - csv
        if save_csv:
            df.to_csv(outpath, index=False)
        # - json
        if save_json:
            with open(outpath.replace('.csv', '.json'), 'w') as f:
                json.dump(results, f)
        # - error report
        # todo: Would be good to have all enclave_wrangler requests basically wrap around python `requests` and also
        #  ...utilize this error reporting, if they are saving to disk.
        if last_response.status_code >= 400:
            error_report: Dict = {'request': last_response.url, 'response': last_response.json()}
            with open(os.path.join(outdir, f'latest - error {last_response.status_code}.json'), 'w') as file:
                json.dump(error_report, file)
            curl_str = f'curl -H "Content-type: application/json" ' \
                       f'-H "Authorization: Bearer $OTHER_TOKEN" {last_response.url}'
            with open(os.path.join(outdir, f'latest - error {last_response.status_code} - curl.sh'), 'w') as file:
                file.write(curl_str)

        return df

    def get_link_types(self, use_cache_if_failure=False) -> List[Union[Dict, str]]:
        """Get link types

        https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-linked-objects/

        todo: This doesn't work on Joe's machine, in PyCharm or shell. Works for Siggie. We both tried using
          PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN (we use the same one) instead as well- 2022/12/12
        todo: What is the UUID starting with 00000001?
        todo: Do equivalent of `jq '..|objects|.apiName//empty'` here so that what's returned from response.json() is
          the also a List[str], like what's 'cached' here.

        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
        "https://unite.nih.gov/ontology-metadata/api/ontology/linkTypesForObjectTypes" --data '{
            "objectTypeVersions": {
                "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                "00000001-9834-2acf-8327-ecb491e69b5c"
            }
        }' | jq '..|objects|.apiName//empty'
        """
        # cached: 2022/12/12
        cached_types: List[str] = [
            'cohortLinks',
            'cohortVersions',
            'conceptSetBundleItem',
            'conceptSetTag',
            'conceptSetVersionChangeAcknowledgement',
            'conceptSetVersionInfo',
            'conceptSetVersions',
            'conceptSetVersionsCreatedForThisResearchProject',
            'consumedConceptSetVersion',
            'consumingProtocolSection',
            'createdOmopConceptSetVersions',
            'creator',
            'documentationNodeRv',
            'draftCohortLinks',
            'intendedDomainTeam',
            'intendedResearchProject',
            'omopConceptChange',
            'omopConceptDomains',
            'omopConceptSetVersion',
            'omopConceptSetVersionIntendedForDT',
            'omopConceptSetVersionItem',
            'omopConceptSetVersions',
            'omopconceptSet',
            'omopconceptSetChildVersion',
            'omopconceptSetContainer',
            'omopconceptSetParentVersion',
            'omopconceptSetReview',
            'omopconcepts',
            'omopconceptsets',
            'omopvocabularyVersion',
            'producedConceptSetVersion',
            'producingProtocolSection',
            'researchProject',
            'revisedconceptSetVersionChangeAcknowledgement',
            'revisedomopconceptSet',
        ]

        # noinspection PyBroadException
        try:
            data = {
                "objectTypeVersions": {
                    "ri.ontology.main.object-type.a11d04a3-601a-45a9-9bc2-5d0e77dd512e":
                        "00000001-9834-2acf-8327-ecb491e69b5c"
                }
            }
            url = f'{self.base_url}/ontology-metadata/api/ontology/linkTypesForObjectTypes'
            response = requests.post(url, headers=self.headers, data=data)
            # TODO:
            #   change to:
            #   response = enclave_post(url, data=data)
            response_json: List[Dict] = response.json()
            return response_json
        except Exception as err:
            if use_cache_if_failure:
                return cached_types
            raise err

    def get_object_links(self, object_type: str, object_id: str, link_type: str) -> Response:
        """Get links of a given type for a given object

        Cavaets
        - If the `link_type` is not valid for a given `object_type`, you'll get a 404 not found.
        """
        return make_objects_request(f'objects/{object_type}/{object_id}/links/{link_type}')


def run(request_types: List[str]) -> Dict[str, Dict]:
    """Run"""
    client = EnclaveClient()
    request_funcs: Dict[str, Callable] = {
        'objects': client.get_objects_by_type,
        'object_types': client.get_obj_types,
        'link_types': client.get_link_types,
    }
    results = {}
    for req in request_types:
        results[req] = request_funcs[req]()
        # if req == 'object_types':
        #     print('\n'.join([t['apiName'] for t in results[req]['types']]))
    return results


def download_favorite_objects(fav_obj_names: List[str] = FAVORITE_OBJECTS, force_if_exists=False):
    """Download objects of interest"""
    client = EnclaveClient()
    for o in fav_obj_names:
        outdir = os.path.join(OUTDIR_OBJECTS, o)
        exists = os.path.exists(outdir)
        if not exists or (exists and force_if_exists):
            client.get_objects_by_type(o, outdir=outdir)


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
        '-f', '--downoad-favorite-objects',
        action='store_true', help='Download favorite objects as CSV and JSON.')
    kwargs = parser.parse_args()
    kwargs_dict: Dict = vars(kwargs)
    if kwargs_dict['download_favorite_objects']:
        download_favorite_objects()
    else:
        del kwargs_dict['download_favorite_objects']
        run(**kwargs_dict)


if __name__ == '__main__':
    cli()
