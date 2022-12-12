"""Tests

How to run:
    python -m unittest discover

TODO's
 - Test framework: Current implementation is ad-hoc for purposes of development.
"""
import requests
import unittest


BACKEND_URL_BASE = 'http://127.0.0.1:8000/'


class TestBackend(unittest.TestCase):

    def setup(self):
        """always runs first"""
        pass

    def tearDown(self) -> None:
        """always runs last"""
        pass

    def test_csets_update(self):
        """Test backend: csets_update
        Prereq: Server must be running"""
        # TODO: make a put request: requests.put(url, data, params, header)
        # TODO: Change this to make a temporary copy of the file, update that, push, then delete tempfile & push again.
        # TODO: can improve by using 'mock':
        #  https://betterprogramming.pub/why-you-should-use-a-put-request-instead-of-a-post-request-13b593b6e67c
        url = BACKEND_URL_BASE + 'datasets/csets'
        response = requests.put(url=url, json={
            'dataset_path': 'test/heroes.csv',
            'row_index_data_map': {
                3: {
                    'first_name': 'Spider',
                    'last_name': 'Man'
                }
            }
        }).json()
        self.assertEqual(response['result'], 'success')


if __name__ == '__main__':
    unittest.main()
