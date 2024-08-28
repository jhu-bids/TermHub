"""Tests

How to run:
    python -m unittest discover
"""
import os
import sys
import unittest
from pathlib import Path
from typing import Union

THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(THIS_DIR).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.db.resolve_fetch_failures_excess_items import resolve_fetch_failures_excess_items
from backend.db.utils import run_sql, sql_query
from enclave_wrangler.objects_api import fetch_cset_and_member_objects
from test.test_backend.db.test_utils import FetchAuditTestRunner
from test.utils import TEST_SCHEMA


# todo: could create some more test cases (i) too many expressions, (ii) >100k members, (iii) 0 members?
class TestBackendResolveFetchFailures(FetchAuditTestRunner):
    """Inherits from the FetchAudit test class to get setup/teardown methods.

    Mock data: good examples
    Couldn't find an example of a failure due to excessive members, fetching between 2023/01/01 and 2023/07/08
    - LongCovid (v1)
      codeset_id: 112182256
      Didn't show up in enclave; strange: https://github.com/jhu-bids/TermHub/pull/465#discussion_r1257384096
      This one has over 10k expression items, and fails.
    Mock data: bad examples
    - Hope Termhub Test (v3)
      codeset_id: 946809371
      https://unite.nih.gov/workspace/module/view/latest/ri.workshop.main.module.5a6c64c0-e82b-4cf8-ba5b-645cd77a1dbf
      This one has 53,998 concept set members, but it actually fetches successfully. Is the limit 100k?
    - [DRAFT] ag - test
      codeset_id: 1000029533
      Firstly, 'isDraft': True. Secondly, it has 0 expression items, so will have 0 members as consequence.
    - [DRAFT] [DM]Type2 Diabetes Mellitus
      codeset_id: 408119970
      'isDraft': True. Has 403 expression items though.

    run_live_fetch: If True, will run fetch_cset_and_member_objects() live w/ case known to produce failure, rather than
    premade mock failure data. The purpose of this is that it will also test that fetch_cset_and_member_objects()
    correctly flags the issue."""
    run_live_fetch = False
    mock_data = [{'table': 'code_sets', 'primary_key': 112182256, 'status_initially': 'fail-excessive-items',
                  'comment': 'Unit testing.'}]

    def _failure_status_query(self, pk: Union[int, str]):
        """Check status of fetch failure and its possible resolution"""
        result = sql_query(self.con, f"SELECT success_datetime FROM fetch_audit WHERE primary_key = '{pk}';")
        results2 = result[-1]
        return results2

    # todo: A better test would be to actually run this in test_n3c, and check before/after that actual data is inserted
    @unittest.skip("Broken. See: https://github.com/jhu-bids/TermHub/issues/829")
    def test_resolve_fetch_failures_excess_items(self):
        """Test resolve_fetch_failures_excess_items()"""
        pk = self.mock_data[0]['primary_key']
        # mock_data: setUpClass will have inserted by now
        if self.run_live_fetch:
            run_sql(self.con, f"DELETE FROM fetch_audit WHERE primary_key = '{pk}' AND comment LIKE 'Unit testing.%';")
            fetch_cset_and_member_objects(codeset_ids=[pk])
        status1 = self._failure_status_query(pk)
        # todo: Ideally should be able to pass specific failures. What if actual failures exist that aren't test cases?
        #  the it will run those as well.
        resolve_fetch_failures_excess_items(TEST_SCHEMA, 24)
        status2 = self._failure_status_query(pk)
        self.assertNotEqual(status1, status2)

# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()
