"""Tests

How to run:
    python -m unittest discover

todo: when finished developing these tests, revert to actual test
 - revert class name to TestGraph
 - revert method names: tst_ -> test_
 - revert file name: tst_ -> test_
 - revert bit at bottom of file
 - revert asserts to self.assert*
TOD: for big JSON, save without indent
"""
import asyncio
import os
import subprocess
import sys
import csv
from io import StringIO
import json
# import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple

from networkx import DiGraph

THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.routes.graph import indented_concept_list, get_connected_subgraph, REL_GRAPH


THIS_STATIC_DIR = THIS_DIR / 'static'
STATIC_DIR_get_connected_subgraph = THIS_STATIC_DIR / 'get_connected_subgraph'
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


# class TestGraph(unittest.TestCase):
class TstGraph:
    """Tests for graph.py"""
    test_cases: List[Dict] = []

    @staticmethod
    def _get_test_cases() -> List[Dict]:
        """Set up"""
        csv_file = StringIO(TEST_CASES_FAST.strip())
        cases: List[Dict] = list(csv.DictReader(csv_file, delimiter=',', quotechar='"'))
        for case in cases:
            for k, v in case.items():
                if k == 'codeset_ids':
                    case[k] = v.split(',')
        return cases

    @staticmethod
    def _save_output(
        test_name: str, sg: DiGraph, nodes_in_graph: Set[int], preferred_concept_ids: Set[int],
        orphans_not_in_graph: Set[int], hidden: Dict[str, Set[int]], minify_threshold=1000, base_case=False
    ):
        """Save outputs
        :param minify_threshold: If the number of records in the JSON is greater than this, will save minified, else
        will use indent of 4.
        :param base_case: If True, this will be considered the new base case for testing against in the future, and
        outputs will be saved not to a hash subfolder, but to STATIC_DIR_get_connected_subgraph. For reference, the hash
         will be saved in _base_case_hash.txt."""
        # Find commit hash & determine how to use it
        hash_proc = subprocess.run(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, text=True, check=True)
        git_hash = hash_proc.stdout.strip()[0:7]
        subdir = STATIC_DIR_get_connected_subgraph
        subdir = subdir / f'{git_hash}' if not base_case else subdir
        subdir.mkdir(parents=True, exist_ok=True)
        path = subdir / f'{test_name}.json'
        if base_case:
            with open(subdir / '_base_case_hash.txt', 'w') as f:
                f.write(git_hash)
        # Format & save output
        normalized_hidden = {k: sorted(list(v)) for k, v in hidden.items()}
        results = {
            'sg.edges': sorted(list(sg.edges)),
            'nodes_in_graph': sorted(list(nodes_in_graph)),
            'preferred_concept_ids': sorted(list(preferred_concept_ids)),
            'orphans_not_in_graph': sorted(list(orphans_not_in_graph)),
            'hidden': normalized_hidden,
        }
        n_records = sum([len(v) for k, v in results.items()])
        indent = None if n_records > minify_threshold else 4
        with open(path, 'w') as f:
            f.write(json.dumps(results, indent=indent))

    # this is not currently used. It needs modification after changes to get_connected_subgraph()
    async def _create_inputs__get_connected_subgraph_NEEDS_REPAIR(self):
        """Test indented_concept_list()"""
        for test_type, test_name, codeset_ids, timeout_secs in [x.values() for x in self._get_test_cases()]:
            # Creat output files
            sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = \
                get_connected_subgraph(REL_GRAPH, codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            self._save_output(test_name, sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden,
                              base_case=True)

    async def tst_get_connected_subgraph(self, only_fast_cases=True, save_output=True):
        """Test indented_concept_list()"""
        # Get results
        expected_actual_by_test: Dict[str, Tuple[Dict, Dict]] = {}
        for test_type, test_name, codeset_ids, timeout_secs in [x.values() for x in self._get_test_cases()]:
            # Do just 1 fast test case, or all test cases?
            if only_fast_cases and test_name not in ['many-small', 'single-small', 'single-small-second-time']:
                continue
            # Expected
            input_path = STATIC_DIR_get_connected_subgraph / f'{test_name}.json'
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
            nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden = \
                get_connected_subgraph(REL_GRAPH, codeset_ids, EXTRA_CONCEPT_IDS, HIDE_VOCABS)
            sg = REL_GRAPH.subgraph(nodes_in_graph.union(missing_in_between_nodes))
            actual = {
                'sg.edges': set(sg.edges),
                'nodes_in_graph': sg.nodes,
                'preferred_concept_ids': preferred_concept_ids,
                'orphans_not_in_graph': orphans_not_in_graph,
                'hidden': hidden,
            }
            # Store results to test at end
            expected_actual_by_test[test_name] = (expected, actual)
            # Save output
            if save_output:
                self._save_output(test_name, sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden)

        # Run tests
        # todo: consider looking at diffs between all files and error at end, rather than on first failure
        for test_name, (expected, actual) in expected_actual_by_test.items():
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
