"""Tests for the Enclave objects API

todo: fix: PKs (and other constraints) aren't set, so this inserts again and again without raising ane error.
 When done, reactivate several tests currently being skipped because of #804. Search for #804 or IntegrityError
 background: originally thought the issue was this: https://github.com/jhu-bids/TermHub/issues/803, but it's #804
"""
import json
import os
import pickle
from copy import deepcopy

import pytz
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Union

from sqlalchemy import Connection
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, MagicMock

from backend.db.config import PG_DATATYPES_BY_GROUP
from enclave_wrangler.utils import JSON_TYPE

THIS_TEST_DIR = Path(os.path.dirname(__file__))
TEST_DIR = THIS_TEST_DIR.parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.utils import delete_obj_by_composite_key, get_db_connection, run_sql, sql_count, sql_query
from enclave_wrangler.models import OBJECT_TYPE_TABLE_MAP, convert_row, field_name_mapping, pkey
from enclave_wrangler.objects_api import LINK_TYPES_RID, concept_enclave_to_db, \
    concept_expression_enclave_to_db, concept_set_container_enclave_to_db, cset_obj_field_datatypes, \
    cset_objs_set_missing_fields_to_null, cset_version_enclave_to_db, \
    csets_and_members_to_db, fetch_cset_and_member_objects, all_new_objects_to_db, \
    get_concept_set_version_members, update_cset_metadata_from_objs
from enclave_wrangler.objects_api import get_object_types, get_link_types, get_object_links, get_age_of_utc_timestamp, \
    get_csets_over_threshold
from test.utils_db_refresh_test_wrapper import DbRefreshTestWrapper


TEST_INPUT_DIR = THIS_TEST_DIR / 'input'
TEST_SCHEMA = 'test_n3c'
YESTERDAY: str = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'  # works: 2023-01-01T00:00:00.000Z


class TestObjectsApi(DbRefreshTestWrapper):

    con: Connection

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.con = get_db_connection(schema=TEST_SCHEMA)

    @classmethod
    def tearDownClass(cls):
        """Cleanly close down test class"""
        cls.con.close()

    def _raises_err_on_duplicate_insert_test(self, table: str, obj_id: Union[int, str], func: Callable):
        """Inserts once so it exists in the table, then inserts again. Error expected."""
        with get_db_connection(schema=TEST_SCHEMA) as con:
            func(con, obj_id, [table], skip_if_already_exists=False)
            self.assertRaises(IntegrityError, func, con, obj_id, [table], skip_if_already_exists=False)

    # todo: after completing this 'test', create func for it in backend/db and call/assert here
    #  - what is the ultimate goal? how many tables are we refreshing?
    # todo: also add test for get_new_objects()
    # def test_fetch_cset_and_member_objects(self):
    #     """Test fetch_cset_and_member_objects()"""
    #     csets_and_members: Dict[str, List] = fetch_cset_and_member_objects(since=yesterday)
    #     # todo: what kind of assert?

    @unittest.skip("Skipping failing test for now. See: https://github.com/jhu-bids/TermHub/issues/804")
    def test_concept_expression_enclave_to_db__raises_err(self):
        """Test concept_expression_enclave_to_db() throws err when expected.
        Inserts once so it exists in the table, then inserts again."""
        table = 'concept_set_version_item'
        obj_id = 'c129643b-0896-4fe3-9722-1191bb0c75ba'  # exists in enclave
        self._raises_err_on_duplicate_insert_test(table, obj_id, concept_expression_enclave_to_db)

    def test_concept_expression_enclave_to_db(self):  # aka test_concept_set_version_item_enclave_to_db()
        """Test concept_expression_enclave_to_db()"""
        table = 'concept_set_version_item'
        obj_id = '479356-3023361'  # exists in enclave
        con: Connection = self.con
        n1: int = sql_count(con, table)
        concept_expression_enclave_to_db(self.con, obj_id, [table])
        n2: int = sql_count(con, table)
        self.assertGreater(n2, n1)
        # Teardown
        run_sql(con, f"DELETE FROM {table} WHERE item_id = '{obj_id}';")

    @unittest.skip("Skipping failing test for now. See: https://github.com/jhu-bids/TermHub/issues/804")
    def test_concept_enclave_to_db__raises_err(self):
        """Test concept_enclave_to_db() throws err when expected.
        Inserts once so it exists in the table, then inserts again."""
        table = 'concept'
        obj_id = 3018737  # exists in enclave
        self._raises_err_on_duplicate_insert_test(table, obj_id, concept_enclave_to_db)

    def test_concept_enclave_to_db(self):
        """Test concept_expression_enclave_to_db()"""
        table = 'concept'
        obj_id = 9472  # exists in enclave
        con: Connection = self.con
        n1: int = sql_count(con, table)
        concept_enclave_to_db(con, obj_id, [table])
        n2: int = sql_count(con, table)
        self.assertGreater(n2, n1)
        # Teardown
        run_sql(con, f"DELETE FROM {table} WHERE concept_id = '{obj_id}';")

    # TODO: In addition to #804, 2 other issues:
    #  1. need new failure case. Why was this removed from the DB? I guess we need more dummy/archived cases.
    #  2. is there supposed to be a space at the beginning of the label / obj_id?
    @unittest.skip("Skipping failing test for now. See: https://github.com/jhu-bids/TermHub/issues/804")
    def test_concept_set_container_enclave_to_db__raises_err(self):
        """Test concept_set_container_enclave_to_db() throws err when expected.
        Inserts once so it exists in the table, then inserts again."""
        table = 'code_sets'
        obj_id = ' Casirivimab Monotherapy (Injection route of admin, 120 MG/ML dose minimum)'  # exists in enclave
        self._raises_err_on_duplicate_insert_test(table, obj_id, concept_set_container_enclave_to_db)

    def test_concept_set_container_enclave_to_db(self):
        """Test cset_container_enclave_to_db()"""
        table = 'concept_set_container'
        obj_id = 'HIV Zihao'
        con: Connection = self.con
        n1: int = sql_count(con, table)
        concept_set_container_enclave_to_db(con, obj_id, [table])
        n2: int = sql_count(con, table)
        self.assertGreater(n2, n1)
        # Teardown
        run_sql(con, f"DELETE FROM {table} WHERE concept_set_id = '{obj_id}';")

    @unittest.skip("Skipping failing test for now. See: https://github.com/jhu-bids/TermHub/issues/804")
    def test_cset_version_enclave_to_db__raises_err(self):
        """Test codeset_version_enclave_to_db() throws err when expected
        Inserts once so it exists in the table, then inserts again."""
        table = 'code_sets'
        obj_id = 1  # exists in enclave
        self._raises_err_on_duplicate_insert_test(table, obj_id, cset_version_enclave_to_db)

    def test_cset_version_enclave_to_db(self):
        """Test codeset_version_enclave_to_db()

        Test that can successfully fetch and insert data.
        Also effectively tests test_code_sets_enclave_to_db().
        """
        table = 'code_sets'
        obj_id = 129091261  # doesn't exist in test DB
        con: Connection = self.con
        n1: int = sql_count(con, table)
        cset_version_enclave_to_db(con, obj_id, [table])
        n2: int = sql_count(con, table)
        self.assertGreater(n2, n1)
        # Teardown
        run_sql(con, f"DELETE FROM {table} WHERE codeset_id = '{obj_id}';")

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
        # Setup
        con: Connection = self.con
        n1: int = sql_count(con, 'concept_set_container')
        csets_and_members_to_db(con, csets_and_members, schema=TEST_SCHEMA)
        t1 = datetime.now()  # temp
        n2: int = sql_count(con, 'concept_set_container')
        print('test_csets_and_members_to_db() setup completed in ', (t1 - t0).seconds, ' seconds')  # temp

        # Teardown: single primary key tables
        # TODO: add teardowns for DDL-created tables
        #  'cset_members_items', 'members_items_summary', 'codeset_counts', 'all_csets'
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

    @unittest.skip("Needs implementation.")  # todo: implement
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
        self.assertGreater(1, 0)

    def test_get_concept_set_version_members(self):
        """test get_concept_set_version_members()"""
        obj_id = 563193300
        data = get_concept_set_version_members(obj_id, return_detail='full')
        self.assertGreater(len(data), 0)

    def test_get_object_links(self):
        """Test get_object_links()"""
        # OMOPConceptSet from OMOPConceptSetContainer
        csets: List[Dict] = get_object_links(
            object_type='OMOPConceptSetContainer',
            object_id='Termhub Test',
            link_type='OMOPConceptSet',
            return_type='data',
            expect_single_item=True)
        self.assertEqual(8, len(csets))

        # OmopConceptSetVersionItem from OMOPConceptSet
        items: List[Dict] = get_object_links(
            object_type='OMOPConceptSet',
            object_id=25731524,
            link_type='OmopConceptSetVersionItem')
        self.assertEqual(1, len(items))

        # omopconcepts from OMOPConceptSet
        members: List[Dict] = get_object_links(
            object_type='OMOPConceptSet',
            object_id=25731524,
            link_type='omopconcepts')
        self.assertEqual(18, len(members))

    # TODO: Test these new tests from claude
    #  - https://claude.ai/chat/7f64ea42-7ab2-43c6-9a86-382bdafc26bf
    def test_get_age_of_utc_timestamp(self):
        now = datetime.now(pytz.utc)
        test_timestamp = now - timedelta(hours=2)
        result = get_age_of_utc_timestamp(test_timestamp)
        self.assertAlmostEqual(result, 7200, delta=10)  # Allow for small time differences during test execution

    def test_get_csets_over_threshold(self):
        csets = [
            {'codesetId': 1, 'createdAt': '2023-01-01T00:00:00Z'},
            {'codesetId': 2, 'createdAt': '2023-07-01T00:00:00Z'},
        ]
        result = get_csets_over_threshold(csets, 30, 'cset_ids')
        self.assertEqual(result, {1, 2})

    @classmethod
    def _fetch_csets_from_db(
        cls, limit=2, cset_ids: List[int] = None, convert_to_enclave_object=True
    ) -> Dict[int, Dict]:
        """Fetch some sample code sets from the database.

        :param: limit: If not cset_ids, will fetch n 'limit' csets; just want to make sure multiple sets work"""
        cset_id_str: str = ', '.join([str(x) for x in cset_ids]) if cset_ids else ''
        query: str = f"""SELECT * FROM {TEST_SCHEMA}.code_sets WHERE codeset_id IN ({cset_id_str});""" if cset_ids \
            else f"""SELECT * FROM {TEST_SCHEMA}.code_sets LIMIT {limit};"""
        csets: Dict[int, Dict] = {x['codeset_id']: dict(x) for x in sql_query(cls.con, query)}
        if convert_to_enclave_object:
            csets = {k: convert_row('code_sets', 'OMOPConceptSet', v) for k, v in csets.items()}
        return csets

    def test_update_cset_metadata_from_objs(self):
        """Test update_cset_metadata_from_objs().

        todo: if DB fully up-to-date, the updates will do nothing. Will this affect the test?
         - the best way to always make this test work would be to (a) create a new cset at the beginning of this test
           and update it, or (b) update an existing test cset.
        todo: If the cset is already in code_sets_audit before this test runs, the test will pass, but it will not
         actually be indicative of the test actually working. Ideally, should make sure csets not in that table first.
        """
        # Fetch cases
        pk = 'codesetId'
        con: Connection = self.con
        csets_from_db: Dict[int, Dict] = self._fetch_csets_from_db()
        cset_ids: List[int] = list(csets_from_db.keys())

        # Mutations
        csets_mutated = deepcopy(csets_from_db)
        update_str = 'test-metadata-updates'
        # - figure out data types for each field
        obj_data_types: Dict[str, str] = cset_obj_field_datatypes(TEST_SCHEMA)
        obj_fields: List[str] = list(obj_data_types.keys())
        # - set values
        for cset_id, cset in csets_mutated.items():
            for k, v in cset.items():
                if k == pk:
                    continue
                elif obj_data_types[k] == 'boolean':
                    cset[k] = not v
                elif obj_data_types[k] in PG_DATATYPES_BY_GROUP['numeric']:
                    cset[k] = v + 1 if v else 1
                elif obj_data_types[k] in PG_DATATYPES_BY_GROUP['string']:
                    cset[k] = v + ' - ' + update_str if v else update_str
                elif obj_data_types[k] in PG_DATATYPES_BY_GROUP['datetime']:
                    cset[k] = datetime.now().isoformat() + 'Z'  # will this work for both with/without time zone?
                else:  # unaccounted data type (uuid, json, xml, etc.); probably would result in an err
                    cset[k] = update_str
        # - update db
        update_cset_metadata_from_objs(list(csets_mutated.values()), con)
        csets_mutated_fetched: Dict[int, Dict] = self._fetch_csets_from_db(cset_ids=cset_ids)
        # Assert changes were as expected
        self.assertEqual(csets_mutated, csets_mutated_fetched)
        # Assert everything changed
        for field in [x for x in obj_fields if x != pk]:
            for cset_id in cset_ids:
                self.assertNotEqual(csets_from_db[cset_id][field], csets_mutated_fetched[cset_id][field])

        # Live fetch
        csets_and_members: Dict[str, List[Dict]] = fetch_cset_and_member_objects(
            codeset_ids=cset_ids, flag_issues=False)
        csets_from_enclave_flat: List[Dict] = [x['properties'] for x in csets_and_members['OMOPConceptSet']]
        csets_from_enclave: Dict[int, Dict] = {x[pk]: x for x in csets_from_enclave_flat}
        # - update db
        update_cset_metadata_from_objs(
            list(csets_from_enclave.values()), con, set_missing_fields_to_null=True, schema=TEST_SCHEMA)
        csets_from_enclave_fetched: Dict[int, Dict] = self._fetch_csets_from_db(cset_ids=cset_ids)
        # - fill in any missing fields that weren't in the enclave
        # todo: this effectively tests cset_objs_set_missing_fields_to_null(); consider independent test method
        csets_from_enclave_normalized: List[Dict] = cset_objs_set_missing_fields_to_null(
            list(csets_from_enclave.values()), schema=TEST_SCHEMA)
        csets_from_enclave_normalized: Dict[int, Dict] = {x[pk]: x for x in csets_from_enclave_normalized}
        # Assert changes were as expected
        # - tests (i) that update query works, and (ii) that logic for set_missing_fields_to_null works
        self.assertEqual(csets_from_enclave_normalized, csets_from_enclave_fetched)

        # Fetch audit table
        # todo: could improve by checking field values & addtional update_timestmp field, and precise number of entries
        cset_id_str: str = ', '.join([str(x) for x in cset_ids]) if cset_ids else ''
        query: str = f"""SELECT codeset_id FROM code_sets_audit WHERE codeset_id IN ({cset_id_str});"""
        rows = sql_query(con, query, return_with_keys=False)
        self.assertGreater(len(rows), 2)


# todo: #2 new tests by claude to try
# todo: #1: Wherever I put '#1', consider removing the mock and call the actual function.
#  - perhaps that will be the case for other test methods; not just the ones where '#1' is tagged
# todo: DRYify test methods? There's a lot of logic re-used, but it looks like it wouldn't be ane asy refactor; return
#  values and params differ for each func, for example.
class TestObjectsApiMocks(DbRefreshTestWrapper):
    """Tests that specifically use mock APIs

    Scaffolded by: https://claude.ai/chat/7f64ea42-7ab2-43c6-9a86-382bdafc26bf
    """
    func_cached_return_map = {
        func: os.path.join(TEST_INPUT_DIR, 'test_' + func.__name__, 'input.json')
        for func in [get_object_types, get_link_types]
    }

    def setUp(self):
        """Set up mock connection"""
        self.mock_connection = MagicMock()

    # todo: consider refactors
    #  1. DRYer: just list the functions, instead of their paths, and the paths should just be automatically calculated,
    #   e.g. test_FUNC/input.json.
    #  2. Even DRYer: Maybe just have _read_cached_return() do everything if cached file doesn't exist. In that
    #  case, it'd call another func to do the caching, then exit out with a warning that the test probably isn't set up
    #  yet, and to look at the cached file and set up the test.
    @classmethod
    def setUpClass(cls):
        """Set up inputs: cached return data for functions that use mock API calls

        Important!: There are some cases where the cached file was saved manually rather than as a result of
        setUpClass() running. Below are the functions and why this was done.
        - get_object_types(): It mocks enclave_get(), but then it removes the 'data' key before returning. I needed to
        add it back manually. It'd get a KeyError if the mock data was returned without that key."""
        for func, path in cls.func_cached_return_map.items():
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    json.dump(func(), f)

    def _read_cached_return(self, func: Callable):
        """Read cached return from file"""
        path = self.func_cached_return_map[func]
        with open(path, 'r') as f:
            return json.load(f)

    def _call_func_using_cached_mock_data(self, func: Callable, mock_func: MagicMock, *args, **kwargs) -> JSON_TYPE:
        """Will call func(), interpolating the mock_func() as it runs (via MagicMock), and using previously cached
        return for said mock_func() running in context of func().
        E.g. for func=get_object_types(), mock_func=enclave_get(), it will call get_object_types(), and when
        enclave_get() is called during that function, it will instead use previously cached data."""
        mock_response = MagicMock()
        mock_response.json.return_value: JSON_TYPE = self._read_cached_return(func)
        mock_func.return_value = mock_response
        result: JSON_TYPE = func(*args, **kwargs)
        return result

    @patch('enclave_wrangler.objects_api.enclave_get')  # todo #1
    def test_get_object_types(self, mock_enclave_get):
        """Test get_object_types()

        This test mocks enclave_get(). get_object_types() doesn't really do any mutation. Just tests nothing breaks."""
        result: JSON_TYPE = self._call_func_using_cached_mock_data(get_object_types, mock_enclave_get)
        endpoints = set({obj['apiName'] for obj in result})
        expected_endpoints_we_need = {
            'OMOPConcept', 'OMOPConceptSetContainer', 'OMOPConceptSet', 'OmopConceptSetVersionItem'}
        expected_endpoints_there = expected_endpoints_we_need.intersection(endpoints)
        self.assertEqual(expected_endpoints_we_need, expected_endpoints_there)

    # todo: could also add a test for link_types(), but it is also unused currently.
    @patch('enclave_wrangler.objects_api.enclave_post')  # todo #1
    def test_get_link_types(self, mock_enclave_post):
        """Test get_link_types()"""
        result: JSON_TYPE = self._call_func_using_cached_mock_data(get_link_types, mock_enclave_post)
        # todo: shouldn't this be an option to return from get_link_types()?
        link_types_ids: List[str] = [x['id'] for x in result['linkTypes'][LINK_TYPES_RID]]
        # todo: would be better to list even more link types that we depend upon and would expect, but as of this
        #  writing (2024/07/06), I don't know which if any we are; this function we're testing doesn't have usages.
        link_types_possibly_needed = {'omop-concept-set-to-omop-concept'}
        expected_endpoints_there = link_types_possibly_needed.intersection(link_types_ids)
        self.assertEqual(link_types_possibly_needed, expected_endpoints_there)
