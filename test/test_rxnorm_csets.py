"""Test RxNorm Csets"""
import os
import sys
import unittest
from pathlib import Path


TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = Path(TEST_DIR).parent
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, str(PROJECT_ROOT))


class TestRxNormCsets(unittest.TestCase):

    def test_rxnorm_csets(self):
        """Test RxNorm Csets"""
        pass


if __name__ == '__main__':
    unittest.main()
