"""Tests

TODO's
 - Test framework: Current implementation is ad-hoc for purposes of development.
"""
import requests


BACKEND_URL_BASE = 'http://127.0.0.1:8000/'


def test_csets_update():
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
    if response['result'] != 'success':
        raise RuntimeError(f'Test `test_csets_update`: failure: {str(response)}')
    print('Test `test_csets_update`: success')


def runall():
    """Run all tests"""
    test_csets_update()


if __name__ == '__main__':
    runall()
