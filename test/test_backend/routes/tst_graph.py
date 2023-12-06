"""Tests

How to run:
    python -m unittest discover
"""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from typing import List

from backend.config import CONFIG

TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.routes.graph import indented_concept_list


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


# todo: at end, revert class, method, and file name from tst -> test
# class TestGraph(unittest.TestCase):
class TstGraph:

    async def tst_indented_concept_list(self):
        """Test indented_concept_list()"""
        # todo; enable test cases from CSV
        # csv_file = StringIO(TEST_CASES_FAST)
        # reader = csv.DictReader(csv_file)
        # test_cases_list = list(reader)
        test_case = [1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299]

        # CONFIG['importer'] = 'app.py'
        tree: List = await indented_concept_list(
            codeset_ids=test_case, extra_concept_ids=[], hide_vocabs=['RxNorm Extension'])
        # todo: assertions
        print()


# Uncomment this and run this file and run directly to run all tests
# if __name__ == '__main__':
#     unittest.main()

asyncio.run(TstGraph().tst_indented_concept_list())


