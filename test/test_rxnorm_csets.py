"""Test RxNorm Csets"""
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Union

from requests import Response

from backend.db.utils import get_db_connection, sql_query
from enclave_wrangler.dataset_upload import upload_new_container_with_concepts

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))


class TestRxNormCsets(unittest.TestCase):

    #     'd' Example:
    #     {
    #       "container": {
    #         "concept_set_name": "My test concept set",
    #         "intention": "",
    #         "research_project": "",
    #         "assigned_sme": "",
    #         "assigned_informatician": ""
    #       },
    #       "versions_with_concepts": [{
    #         "omop_concepts": [
    #             {
    #               "concept_id": 45259000,
    #               "includeDescendants": true,
    #               "isExcluded": false,
    #               "includeMapped": true,
    #               "annotation": "This is my concept annotation."
    #             }
    #         ],
    #         "provenance": "Created through TermHub.",
    #         "concept_set_name": "My test concept set",
    #         "limitations": "",
    #         "intention": ""
    #       }]
    #     }
    def test_rxnorm_csets(self):
        """Test RxNorm Csets
        todo: later?: check if already exists in termhub before uploading. where? code_sets.concept_set_version_title
        """
        # TODO: Upload any new concept sets to the enclave
        #  (this will fail if the concept set name already exists)
        #  - fetch this information from table
        #  - then do the whole thing to upload to the enclave
        with get_db_connection() as con:
            csets: List[Dict] = [dict(x) for x in sql_query(con, 'SELECT * FROM rxnorm_med_cset;')]
        responses: List[Dict[str, Union[Response, List[Response]]]] = []
        for cset in csets:
            response: Dict[str, Union[Response, List[Response]]] = upload_new_container_with_concepts(
                concept_set_name=cset['cset_name'],
                intention=d.container['intention'],
                research_project=d.container['research_project'],
                assigned_sme=d.container['assigned_sme'],
                assigned_informatician=d.container['assigned_informatician'],
                versions_with_concepts=d.versions_with_concepts)
            responses.append(response)



if __name__ == '__main__':
    unittest.main()
