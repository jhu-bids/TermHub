"""Tests

How to run:
    python -m unittest discover
"""
import asyncio
import os
import sys
import csv
from io import StringIO
import json
import unittest
from pathlib import Path
from typing import List
from backend.utils import pdump

from backend.config import CONFIG

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.routes.graph import indented_concept_list, get_connected_subgraph, REL_GRAPH


TEST_CASES_FAST = """
testType,testName,codeset_ids,timeoutSeconds
single small,single-small,1000002363,30
many small,many-small,"1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299",45
single small,single-small-second-time,1000002363,30
"""

TEST_CASES_HOLD = """
testType,testName,codeset_ids,timeoutSeconds
mixed 6000 to 21000,Sulfonylureas,"417730759, 423850600, 966671711, 577774492",120
single 2000,autoimmune 1,101398605,180
mixed 30 to 3000,autoimmune 2,"101398605, 947369784, 287650725, 283328624, 115052941",240
single 30000,antibiotics 1,909552172,180
"""

TEST_CASES = TEST_CASES_FAST

csv_file = StringIO(TEST_CASES_FAST.strip())
reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
test_cases_list = list(reader)

extra_concept_ids = []
hide_vocabs = ['RxNorm Extension']

results_from = {
    'date': '2023-12-18',
    'commit': '660394d',
}
results = {
    'get_connected_subgraph': {
        'single-small': {
            'results': [[[442793, 4034964], [4129519, 43531010]],
                        [4174977, 43531010, 4161671, 4327944, 4221962, 4237068, 4034962, 4034964, 4294429, 4102176,
                         45766050, 4224419, 442793, 4016047, 35626038, 35626039, 4162239, 36674752, 43022019, 3172958,
                         4270049, 4044391, 4044392, 4129519, 4129524, 4129525, 35625724],
                        [4174977, 43531010, 4161671, 4327944, 4221962, 4237068, 4034962, 4034964, 4294429, 4102176,
                         45766050, 4224419, 442793, 4016047, 35626038, 35626039, 4162239, 36674752, 43022019, 3172958,
                         4270049, 4044391, 4044392, 4129519, 4129524, 4129525, 35625724], [4252356, 44833365], {}]
        }
    }
}

# todo: at end, revert class, method, and file name from tst -> test
# class TestGraph(unittest.TestCase):
class TstGraph:

    async def tst_get_connected_subgraph(self):
        """Test indented_concept_list()"""
        # todo; enable test cases from CSV
        for case in test_cases_list:
            codeset_ids = case['codeset_ids'].split(',')
            sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = (
                get_connected_subgraph(REL_GRAPH, codeset_ids, extra_concept_ids, hide_vocabs))
            # todo: assertions
            j = json.dumps(
                [list(sg.edges), list(nodes_in_graph), list(preferred_concept_ids), list(orphans_not_in_graph), hidden])
            print()


    async def tst_indented_concept_list(self):
        """Test indented_concept_list()"""
        # todo; enable test cases from CSV
        # test_case = [1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299]
        for case in test_cases_list:
            codeset_ids = case['codeset_ids'].split(',')
            tree: List = await indented_concept_list(
                codeset_ids=codeset_ids, extra_concept_ids=extra_concept_ids, hide_vocabs=hide_vocabs)
        # todo: assertions
        print()


# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()

# asyncio.run(TstGraph().tst_indented_concept_list())
asyncio.run(TstGraph().tst_get_connected_subgraph())
