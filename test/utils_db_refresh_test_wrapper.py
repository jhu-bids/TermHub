"""This class is not in utils.py primarily because PyCharm won't run test/utils.py normally unless it is here. It thinks
 that this class is a test clas even though it is intended only as a superclass, simply because it inherits from
 unittest.TestCase, and trys to run its test (does nothing because it's empty), ignoring the 'if __name__' block."""
import unittest

from test.utils import remake_test_schema


class DbRefreshTestWrapper(unittest.TestCase):
    """Runs common setup for all DB refresh related tests"""

    @classmethod
    def setUpClass(cls):
        """setUpClass() meant to run for all subclasses when they call super().setUpClass()"""
        print('DbRefreshTestWrapper: Setting up class; running remake_test_schema()')
        remake_test_schema()
