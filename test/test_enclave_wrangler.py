"""Tests

TODO's
 - 1. Test framework: Current implementation is ad-hoc for purposes of development.
 - 2. Change from validate to apply, or do both
"""
import os

from enclave_wrangler.new_enclave_api import JSON_TYPE, upload_concept, upload_concept_set, upload_draft_concept_set

# todo: replace what I've done here w/ `upload_dataset` eventually if I can. Right now limited by not being able to
#  delete a container.
# from enclave_wrangler.dataset_upload import upload_dataset


TEST_INPUT_DIR = os.path.join(os.path.dirname(__file__), 'input', 'test_enclave_wrangler')


# todo: Can add this test by composing other non-validation tests (then, remove 'PyUnusedLocal' line)
# todo: can just not create container for now, and test simply (i) add/delete versions, (ii) add/delete concepts
# noinspection PyUnusedLocal
def test_dataset_upload(inpath=os.path.join(TEST_INPUT_DIR, 'test_dataset_upload')):
    """Test upload of a new dataset"""
    # TODO: use dataset_upload to upload a palantir-3-file set
    pass

    # TODO: When I create a new draft, does it give me the ID back? because we want to avoid assigning 'internal_id'
    pass

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


def test_upload_concept_set():
    response: JSON_TYPE = upload_concept_set(
        concept_set_id='x', intention='x', research_project='x',
        # TODO: Need to get valid user IDs for these
        # assigned_sme='x',
        # assigned_informatician='x',
        validate=True)
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set', response)


def test_upload_concept():
    response: JSON_TYPE = upload_concept(
        include_descendants=True, concept_set_version_item='x', is_excluded=True, include_mapped=True, validate=True)
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set', response)


def test_upload_draft_concept_set():
    response: JSON_TYPE = upload_draft_concept_set(
        domain_team='x', provenance='x', current_max_version=2.1, concept_set='x', annotation='x', limitations='x',
        intention='x', base_version=1, intended_research_project='x', version_id=1, authority='x', validate=True)
    # self.assertTrue('result' in response and not response['result'] == 'VALID')
    if not('result' in response and response['result'] == 'VALID'):
        print('Failure: test_upload_concept_set', response)


if __name__ == '__main__':
    # test_dataset_upload()  # todo
    test_upload_concept_set()  # ok
    # test_upload_concept()  # ok
    # test_upload_draft_concept_set()  # TODO: not ok; asking Amin
    pass