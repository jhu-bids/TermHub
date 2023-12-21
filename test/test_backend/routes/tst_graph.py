"""Tests

How to run:
    python -m unittest discover

todo: when finished developing these tests, revert to actual test
 - revert class name to TestGraph
 - revert method names: tst_ -> test_
 - revert file name: tst_ -> test_
 - revert bit at bottom of file
 - calling setUpClass at start of each method no longer necessary; will be done automatically
 - revert asserts to self.assert*
"""
import asyncio
import os
import sys
import csv
from io import StringIO
import json
# import unittest
from pathlib import Path
from typing import Dict, List

THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.routes.graph import indented_concept_list, get_connected_subgraph, REL_GRAPH


THIS_INPUT_DIR = THIS_DIR / 'input'
TEST_CASES_FAST = """
testType,testName,codeset_ids,timeoutSeconds
single 2000,autoimmune 1,101398605,180
many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299",45
mixed 6000 to 21000,Sulfonylureas,"417730759, 423850600, 966671711, 577774492",120
mixed 30 to 3000,autoimmune 2,"101398605, 947369784, 287650725, 283328624, 115052941",240
single 30000,antibiotics 1,909552172,180
single small,single-small,1000002363,30
single small,single-small-second-time,1000002363,30
"""
TEST_CASES_HOLD = """
testType,testName,codeset_ids,timeoutSeconds
"""
TEST_CASES = TEST_CASES_FAST
EXTRA_CONCEPT_IDS = []
HIDE_VOCABS = ['RxNorm Extension']
CONNECTED_SUBGRAPH_FILENAME_PATTERN = 'get_connected_subgraph__{}.json'


# class TestGraph(unittest.TestCase):
class TstGraph:
    """Tests for graph.py"""
    test_cases: List[Dict] = []

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        """Set up"""
        csv_file = StringIO(TEST_CASES_FAST.strip())
        cases: List[Dict] = list(csv.DictReader(csv_file, delimiter=',', quotechar='"'))
        for case in cases:
            for k, v in case.items():
                if k == 'codeset_ids':
                    case[k] = v.split(',')
        cls.test_cases = cases

    async def _create_inputs__get_connected_subgraph(self):
        """Test indented_concept_list()"""
        self.setUpClass()  # temp until tests finished
        for test_type, test_name, codeset_ids, timeout_secs in [x.values() for x in self.test_cases]:
            # TODO: temp
            if test_name not in ['antibiotics 1']:
                continue
            input_path = THIS_INPUT_DIR / CONNECTED_SUBGRAPH_FILENAME_PATTERN.format(test_name)
            sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = \
                get_connected_subgraph(REL_GRAPH, codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            #
            normalized_hidden = {k: sorted(list(v)) for k, v in hidden.items()}
            results = {
                'sg.edges': sorted(list(sg.edges)),
                'nodes_in_graph': sorted(list(nodes_in_graph)),
                'preferred_concept_ids': sorted(list(preferred_concept_ids)),
                'orphans_not_in_graph': sorted(list(orphans_not_in_graph)),
                'hidden': normalized_hidden,
            }
            with open(input_path, 'w') as f:
                f.write(json.dumps(results, indent=4))

    async def tst_get_connected_subgraph(self, only_fast_cases=True):
        """Test indented_concept_list()"""
        self.setUpClass()  # temp until tests finished
        for test_type, test_name, codeset_ids, timeout_secs in [x.values() for x in self.test_cases]:
            # Do just 1 fast test case, or all test cases?
            if only_fast_cases and test_name not in ['many-small', 'single-small', 'single-small-second-time']:
                continue
            # Expected
            input_path = THIS_INPUT_DIR / CONNECTED_SUBGRAPH_FILENAME_PATTERN.format(test_name)
            expected_raw = json.load(open(input_path, 'r'))
            expected = {}  # convert JSON serialization back to sets
            for k, v in expected_raw.items():
                if k == 'sg.edges':
                    expected[k] = {tuple(x) for x in v}
                elif k == 'hidden':
                    expected[k] = {k2: set(v2) for k2, v2 in v.items()}
                else:
                    expected[k] = set(v)
            # Actual
            sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = \
                get_connected_subgraph(REL_GRAPH, codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            actual = {
                'sg.edges': set(sg.edges),
                'nodes_in_graph': nodes_in_graph,
                'preferred_concept_ids': preferred_concept_ids,
                'orphans_not_in_graph': orphans_not_in_graph,
                'hidden': hidden,
            }
            # Compare
            for k, v in actual.items():
                # self.assertEqual(v, expected[k], msg=f'Results differ for {k} for test {test_name}')
                assert v == expected[k], f'Results differ for "{k}" in test for "{test_name}"'

    # todo: at some point
    async def tst_indented_concept_list(self):
        """Test indented_concept_list()"""
        # this commented out line not needed anymore?
        # test_case = [1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299]
        for test_type, test_name, codeset_ids, timeout_secs in [x.values() for x in self.test_cases]:
            tree: List = await indented_concept_list(
                codeset_ids=codeset_ids, extra_concept_ids=EXTRA_CONCEPT_IDS, hide_vocabs=HIDE_VOCABS)
            print(tree)


# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()
# asyncio.run(TstGraph().tst_indented_concept_list())
asyncio.run(TstGraph().tst_get_connected_subgraph())
