"""Tests

How to run:
    python -m unittest discover
"""
import os
import sys
from pathlib import Path

from backend.db.resolve_fetch_failures import resolve_fetch_failures
from backend.db.utils import run_sql, sql_query
from enclave_wrangler.objects_api import fetch_cset_and_member_objects
from test.backend_tests.db.test_utils import FetchAuditTestRunner

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


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

    # todo: A better test would be to actually run this in test_n3c, and check before/after that actual data is inserted
    #  but I don't think it'll run cuz it's still missing a few of the new tables; or maybe just 1: csets_to_ignore?
    def test_resolve_fetch_failures(self):
        """Test resolve_fetch_failures()"""
        pk = self.mock_data[0]['primary_key']
        query = lambda: sql_query(self.con, f"SELECT success_datetime FROM fetch_audit WHERE primary_key = '{pk}';")[-1]
        # mock_data: setUpClass will have inserted by now
        if self.run_live_fetch:
            run_sql(self.con, f"DELETE FROM fetch_audit WHERE primary_key = '{pk}' AND comment = 'Unit testing.';")
            fetch_cset_and_member_objects(codeset_ids=[pk])
        status1 = query()
        resolve_fetch_failures()
        status2 = query()
        self.assertNotEqual(status1, status2)


# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()
