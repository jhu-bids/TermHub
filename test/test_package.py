#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for  package."""
import os
import subprocess
import unittest
from glob import glob

from test.config import TEST_STATIC_DIR, TEST_PACKAGES, PKG_NAME
from test.utils import get_args, get_test_suite


class StandardInputOutputTest(unittest.TestCase):
    """Base class for package tests."""

    @classmethod
    def files_dir(cls):
        """Return name of test class."""
        return TEST_STATIC_DIR + cls.__name__

    def input_path(self):
        """Return path of input file folder for test class."""
        return self.files_dir() + '/input/'

    def output_path(self):
        """Return path of output file folder for test class."""
        return self.files_dir() + '/output/'

    def input_files(self, directory=''):
        """Return paths of input files in given directory.

        Args:
            directory (str): Path to target directory including input files.

        Returns:
            list: Input files.
        """
        path = self.input_path() + directory + '/'
        all_files = glob(path + '*')
        # With sans_temp_files, you can have XlsForms open while testing.
        sans_temp_files = [x for x in all_files
                           if not x[len(path):].startswith('~$')]
        return sans_temp_files

    def output_files(self):
        """Return paths of input files for test class."""
        return glob(self.output_path() + '*')

    @staticmethod
    def _dict_options_to_list(options):
        """Converts a dictionary of options to a list.

        Args:
            options (dict): Options in dictionary form, e.g. {
                'OPTION_NAME': 'VALUE',
                'OPTION_2_NAME': ...
            }

        Returns:
            list: A single list of strings of all options of the form
            ['--OPTION_NAME', 'VALUE', '--OPTION_NAME', ...]

        """
        new_options = []

        for k, v in options.items():
            new_options += ['--'+k, v]

        return new_options

    def standard_test(self, options={}):
        """Checks standard convert success.

        Args:
            options (dict): Options in dictionary form, e.g. {
                'OPTION_NAME': 'VALUE',
                'OPTION_2_NAME': ...
            }

        Side effects:
            assertEqual()
        """
        out_dir = self.output_path()

        subprocess.call(['rm', '-rf', out_dir])
        os.makedirs(out_dir)
        command = \
            ['python3', '-m', PKG_NAME] + \
            ['--arg1'] + self.input_files('arg1') + \
            ['--arg2', 'put arg2 here'] + \
            ['--outpath', out_dir]
        if options:
            command += StandardInputOutputTest._dict_options_to_list(options)
        subprocess.call(command)

        expected = 'N files: ' + str(len(self.input_files()))
        actual = 'N files: ' + str(len(self.output_files()))
        self.assertEqual(expected, actual)


class AInputOutputTest(StandardInputOutputTest):
    """A standard test case"""

    def test_convert(self):
        """Test that works as expected."""
        self.standard_test()


if __name__ == '__main__':
    PARAMS = get_args()
    TEST_SUITE = get_test_suite(TEST_PACKAGES)
    unittest.TextTestRunner(verbosity=1).run(TEST_SUITE)

    if not PARAMS.doctests_only:
        unittest.main()
