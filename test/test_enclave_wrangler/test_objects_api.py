"""Tests

Can run all tests in all files by running this from root of TermHub:
    python -m unittest discover
"""
import os
import pickle
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from sqlalchemy.exc import IntegrityError

THIS_TEST_DIR = Path(os.path.dirname(__file__))
TEST_DIR = THIS_TEST_DIR.parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
TEST_INPUT_DIR = TEST_DIR / 'input'
TEST_SCHEMA = 'test_n3c'
YESTERDAY: str = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'  # works: 2023-01-01T00:00:00.000Z

from backend.db.utils import delete_obj_by_composite_key, get_db_connection, run_sql, sql_count
from enclave_wrangler.models import OBJECT_TYPE_TABLE_MAP, field_name_mapping, pkey
from enclave_wrangler.objects_api import concept_enclave_to_db, \
    concept_expression_enclave_to_db, concept_set_container_enclave_to_db, cset_version_enclave_to_db, \
    csets_and_members_to_db, fetch_cset_and_member_objects, all_new_objects_to_db, \
    get_concept_set_version_members


class TestObjectsApi(unittest.TestCase):

    # todo: after completing this 'test', create func for it in backend/db and call/assert here
    #  - what is the ultimate goal? how many tables are we refreshing?
    # todo: also add test for get_new_objects()
    # def test_fetch_cset_and_member_objects(self):
    #     """Test fetch_cset_and_member_objects()"""
    #     csets_and_members: Dict[str, List] = fetch_cset_and_member_objects(since=yesterday)
    #     # todo: what kind of assert?

    # TODO: Seems to be failing now because using test_n3c instead of n3c even though con schema=TEST_SCHEMA

    def test_concept_expression_enclave_to_db(self):  # aka test_concept_set_version_item_enclave_to_db()
        """Test concept_expression_enclave_to_db()"""
        table = 'concept_set_version_item'
        with get_db_connection(schema=TEST_SCHEMA) as con:
            # Failure case: exists in test DB
            item_id_fail = 'c129643b-0896-4fe3-9722-1191bb0c75ba'
            self.assertRaises(IntegrityError, concept_expression_enclave_to_db, con, item_id_fail, [table], False)

            # Success case:  doesn't exist in test DB
            item_id_succeed = '479356-3023361'
            n1: int = sql_count(con, table)
            concept_expression_enclave_to_db(con, item_id_succeed, [table])
            n2: int = sql_count(con, table)
            self.assertGreater(n2, n1)
            # Teardown
            run_sql(con, f"DELETE FROM {table} WHERE item_id = '{item_id_succeed}';")

    def test_concept_enclave_to_db(self):
        """Test concept_expression_enclave_to_db()"""
        with get_db_connection(schema=TEST_SCHEMA) as con:
            table = 'concept'
            # Failure case: exists in test DB
            concept_id_fail = 3018737
            self.assertRaises(IntegrityError, concept_enclave_to_db, con, concept_id_fail, [table], False)

            # Success case: doesn't exist in test DB
            concept_id_succeed = 9472
            n1: int = sql_count(con, table)
            concept_enclave_to_db(con, concept_id_succeed, [table])
            n2: int = sql_count(con, table)
            self.assertGreater(n2, n1)
            # Teardown
            run_sql(con, f"DELETE FROM {table} WHERE concept_id = '{concept_id_succeed}';")

    def test_concept_set_container_enclave_to_db(self):
        """Test cset_container_enclave_to_db()"""
        table = 'concept_set_container'
        # TODO: Switch back to test schema after
        with get_db_connection(schema=TEST_SCHEMA) as con:
            # Failure case: exists in test DB
            # TODO: need new failure case. Why was this removed from the DB? I guess we need more dummy/archived cases.
            # concept_set_id_fail = ' Casirivimab Monotherapy (Injection route of admin, 120 MG/ML dose minimum)'
            # self.assertRaises(
            #     IntegrityError, concept_set_container_enclave_to_db, con, concept_set_id_fail, [table], False)

            # Success case:  doesn't exist in test DB
            concept_set_id_succeed = 'HIV Zihao'
            n1: int = sql_count(con, table)
            concept_set_container_enclave_to_db(con, concept_set_id_succeed, [table])
            n2: int = sql_count(con, table)
            self.assertGreater(n2, n1)
            # Teardown
            run_sql(con, f"DELETE FROM {table} WHERE concept_set_id = '{concept_set_id_succeed}';")

    def test_cset_version_enclave_to_db(self):  # aka test_code_sets_enclave_to_db()
        """Test codeset_version_enclave_to_db()"""
        table = 'code_sets'
        with get_db_connection(schema=TEST_SCHEMA) as con:
            # Failure case
            codeset_id_fail = 1  # exists in test DB
            self.assertRaises(IntegrityError, cset_version_enclave_to_db, con, codeset_id_fail, [table], False)

            # Success case
            codeset_id_succeed = 1049370  # doesn't exist in test DB
            n1: int = sql_count(con, table)
            cset_version_enclave_to_db(con, codeset_id_succeed, [table], )
            n2: int = sql_count(con, table)
            self.assertGreater(n2, n1)
            # Teardown
            run_sql(con, f"DELETE FROM {table} WHERE codeset_id = '{codeset_id_succeed}';")

    def test_csets_and_members_to_db(self):
        """Test csets_and_members_enclave_to_db()
        todo: Change static counts/asserts to dynamic?
        todo: Add more asserts?"""
        # pickle: based on 2023/05/23 run of: get_new_cset_and_member_objects(since=yesterday)
        t0 = datetime.now()  # temp
        pickle_path = os.path.join(TEST_INPUT_DIR, 'test_csets_and_members_enclave_to_db', 'objects.pkl')
        with open(pickle_path, 'rb') as file:
            csets_and_members: Dict[str, List] = pickle.load(file)
        # todo: v[0:n]: should this be temp or permanent to make test run faster? Making it so that there's not a lot?
        with get_db_connection(schema=TEST_SCHEMA) as con:
            # Setup
            n1: int = sql_count(con, 'concept_set_container')
            csets_and_members_to_db(con, TEST_SCHEMA, csets_and_members)
            t1 = datetime.now()  # temp
            n2: int = sql_count(con, 'concept_set_container')
            print('test_csets_and_members_to_db() setup completed in ', (t1 - t0).seconds, ' seconds')  # temp

            # Teardown: single primary key tables
            # TODO: add teardowns for DDL-created tables (except for cset_members_items_plus, which is a view)
            #  'cset_members_items', 'members_items_summary', 'cset_members_items_plus', 'codeset_counts', 'all_csets'
            #   - maybe for now i can do this before this next section. but then I can move it to the end.
            #   - i'd like to ideally keep it with this section and do things dynamically, but i think I should program
            #   it statically first until I become more familiar with these tables
            #     'OMOPConceptSetContainer': [
            #     'OMOPConceptSet': [
            #     'OmopConceptSetVersionItem': [
            #     'OMOPConcept': [
            # TODO: IGNORE above? see simplified notes in workflowy
            # for objects in csets_and_members['OMOPConceptSet']:
            #     print()
            # todo: Performance: Change delete to use sql_in() instead of itering objects
            for object_type_name, objects in csets_and_members.items():
                tables = OBJECT_TYPE_TABLE_MAP[object_type_name]
                for obj in objects:
                    obj = obj['properties'] if 'properties' in obj else obj
                    obj_pk = pkey(object_type_name)
                    obj_id = obj[obj_pk]
                    for table in tables:
                        table_pk = field_name_mapping(object_type_name, table, obj_pk)
                        run_sql(con, f'DELETE FROM {table} WHERE {table_pk} = (:obj_id)', {'obj_id': obj_id})
            # Teardown: composite primary key tables
            for cset in csets_and_members['OMOPConceptSet']:
                for member in cset['member_items']:
                    key_ids = {
                        'codeset_id': cset['properties']['codesetId'],
                        'concept_id': member['properties']['conceptId']}
                    delete_obj_by_composite_key(con, 'concept_set_members', key_ids)

            # Asserts
            # TODO: add asserts for more tables
            t2 = datetime.now()  # temp
            print('test_csets_and_members_to_db() setup & teardown completed in ', (t2 - t0).seconds, ' seconds')  # temp
            self.assertEqual(n2, n1 + len(csets_and_members['OMOPConceptSetContainer']))

    def test_update_db_with_new_objects(self):
        """Test update_db_with_new_objects()"""
        # todo: get latest rows from 4 tables
        new_objects: Dict[str, List] = fetch_cset_and_member_objects(since=YESTERDAY)
        all_new_objects_to_db(new_objects)
        # todo: check that latest row is different? (assuming that there were actually any new objects
        pass
        # todo: teardown
        #  (a) inserts: delete (can I get PK / index back from query that inserted?
        #  (b) updates: I think I need to back them up before updating them
        #  (c) any way I can do some sort of migrated versioning / rollback of DB instead? (e.g. Alembic)

    def test_get_concept_set_version_members(self):
        """test get_concept_set_version_members()"""
        codeset_id = 563193300
        data = get_concept_set_version_members(codeset_id, return_detail='full')
        self.assertGreater(len(data), 0)
