"""Tests

TODO's
 - 1. Test framework: Current implementation is ad-hoc for purposes of development.
 - 2. Change from validate to apply, or do both
"""
import os
import sys


TEST_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(TEST_DIR, '..')
# todo: why is this necessary in this case and almost never otherwise?
# https://stackoverflow.com/questions/33862963/python-cant-find-my-module
sys.path.insert(0, PROJECT_ROOT)
from enclave_wrangler.new_enclave_api import JSON_TYPE, upload_concept_set, add_concept_via_set, \
    upload_draft_concept_set
from enclave_wrangler.dataset_upload import post_to_enclave
from enclave_wrangler.config import PALANTIR_ENCLAVE_USER_ID_1

# todo: replace what I've done here w/ `upload_dataset` eventually if I can. Right now limited by not being able to
#  delete a container.
# from enclave_wrangler.dataset_upload import upload_dataset


TEST_INPUT_DIR = os.path.join(TEST_DIR, 'input', 'test_enclave_wrangler')


# todo: Can add this test by composing other non-validation tests (then, remove 'PyUnusedLocal' line)
# todo: can just not create container for now, and test simply (i) add/delete versions, (ii) add/delete concepts
# noinspection PyUnusedLocal
def test_dataset_upload(inpath=os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')):
    """Test upload of a new dataset"""
    # TODO: use dataset_upload to upload a palantir-3-file set
    post_to_enclave(inpath, create_cset_container=False, create_cset_versions=False)

    # TODO: do actual uploads as well; but this requires "teardown" completion first
    # post_to_enclave(inpath)

    # TODO: teardown
    #  1. "apiName": "delete-omop-concept-set-version"
    #  2. there's no endpoint to delete a concept-set-container (i think that's the one). but there is a way to archive
    #    ...so for now, we can use the following; and Amin might add a way for us to delete a specific concept set with
    #    ...a single known name, just for us, for our unit tests:
    #     {
    #       "apiName": "archive-concept-set",
    #       "description": "Sets Concept Set 'archived' property to true so that it no longer appears in browser",
    #       "rid": "ri.actions.main.action-type.cbc3643b-cca4-4772-ae2d-ae7036a6798b",
    #       "parameters": {
    #         "concept-set": {
    #           "description": "",
    #           "baseType": "OntologyObject"
    #         }
    #       }
    #     },
    pass


def test_upload_concept_set(user_id=PALANTIR_ENCLAVE_USER_ID_1):
    response: JSON_TYPE = upload_concept_set(
        concept_set_id='x', intention='x', research_project='x', assigned_sme=user_id,
        assigned_informatician=user_id)
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set\n', response, file=sys.stderr)


def test_upload_concept():
    response: JSON_TYPE = add_concept_via_set(
        include_descendants=True, concept_set_version_item='x', is_excluded=True, include_mapped=True)
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set\n', response, file=sys.stderr)


def test_upload_draft_concept_set():
    response: JSON_TYPE = upload_draft_concept_set(
        domain_team='x', provenance='x', current_max_version=2.1, concept_set='x', annotation='x', limitations='x',
        intention='x', base_version=1, intended_research_project='x', version_id=1, authority='x')
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set\n', response, file=sys.stderr)


if __name__ == '__main__':
    test_dataset_upload()  # todo
    # test_upload_concept_set()  # ok
    # test_upload_concept()  # ok
    # test_upload_draft_concept_set()  # TODO: try again after param changes
    pass