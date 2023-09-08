"""Tests

Can run all tests in all files by running this from root of TermHub:
    python -m unittest discover
"""
import unittest
from enclave_wrangler.objects_api import make_objects_request
from backend.db.utils import get_db_connection, sql_query_single_col

TEST_SCHEMA = 'test_n3c'


class TestDatabaseCurrent(unittest.TestCase):

    # TODO: @Siggie: Add test for https://github.com/jhu-bids/TermHub/issues/521 here
    def test_csets_match_enclave(self):  # aka test_concept_set_version_item_enclave_to_db()
        """Test OMOPConceptSet returns same codeset_ids as present in code_sets in db"""
        # with get_db_connection(schema=TEST_SCHEMA) as con:
        with get_db_connection() as con:

            db_codeset_ids = set(sql_query_single_col(con, 'SELECT codeset_id FROM code_sets'))

            enclave_codesets = make_objects_request('OMOPConceptSet', return_type='data', handle_paginated=True)

            enclave_codesets = [cset['properties'] for cset in enclave_codesets]

            archivedContainers = make_objects_request(
                'OMOPConceptSetContainer', query_params={'properties.archived.eq': True},
                return_type='data', handle_paginated=True)
            archivedContainerNames = [container['properties']['conceptSetName'] for container in archivedContainers]

            enclave_codesets = [cset for cset in enclave_codesets if 'conceptSetNameOMOP' in cset.keys() and not cset['conceptSetNameOMOP'] in archivedContainerNames]

            enclave_codeset_ids = set([cset['codesetId'] for cset in enclave_codesets])

            missing_ids_from_db = enclave_codeset_ids.difference(db_codeset_ids)

            if missing_ids_from_db:
                missing_from_db = [cset for cset in enclave_codesets if cset['codesetId'] in missing_ids_from_db]
                drafts = [cset for cset in missing_from_db if cset['isDraft']]
                notdrafts = [cset for cset in missing_from_db if not cset['isDraft']]

            extra_in_db = db_codeset_ids.difference(enclave_codeset_ids)
            if extra_in_db:
                pass
                # get these from database and figure out what's up with them



            self.assertEqual(set(enclave_codeset_ids), set(db_codeset_ids))
