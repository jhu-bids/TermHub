"""New Enclave API

TODO: see todo '#123' in backend/app.py

TODO's
  Want to replace enclave_api.py with this when done
  TO-DO: validate first, then change to do actual post
  TO-DO: find out whats required by doing a validate post
    - There should be API examples in response.json i got for this
    - Probably don't need the random ID we were using for new concept set / version
    - 1 & 2 are the most important.
    - Curl first and command at top of function for easy testing
    - For unit test, use validate url?
  0. Test case file. Might want to write a unit test for this.
    - test_enclave.py. 3 palantir files; just a single concept set.
  1. Create a new concept set
    1.1. Create a new concept set (see: createNewConceptSetDescription; "apiName": "create-new-concept-set",)
    1.2. Create new draft (see: createNewDraft; "apiName": "create-new-draft-omop-concept-set-version",)
      - This will be empty at first; the first draft.
    1.3. Add concepts to the draft.
    1.4. Approve: Turn draft into a version.
    Once first is working, should be able to figure out the second.
  2. Add/remove concepts from existing concept set
    - (Siggie doesn't know the steps)
  3. Change metadata on existing concept set
    - (Siggie doesn't know the steps)

todo's (later/minor/contingent)
  - to-do: contingent: @amin/enclave: Concept set ownership. Right now, personal access token is required. Service token
  (i.e. for bulk import) not allowed. This may create an issue later where, when a user is using TermHub and they upload
  a concept set, we will have to (a) use one of our personal access tokens, in which case it will not show in the
  enclave who really uploaded the concept set; it'll say one of us, or (b) we have the user pass their own personal
  access token. Amin (2022/10/19) said: "decision: onBehalfOf". I suppose this means that we'll add this optional param
  instead of an optional 'owner' param.
  - to-do: would we indeed represent OntologyObject types as Dict?

Notes
- Can't delete a concept-set-container. This is to prevent an accident where we delete something that someone else
depends on. This may change in the future; Amin could allow us to delete a specific concept set with a known name.
However, archive-concept-set is good enough for now.
    {
      "apiName": "",
      "description": "Sets Concept Set 'archived' property to true so that it no longer appears in browser",
      "rid": "ri.actions.main.action-type.cbc3643b-cca4-4772-ae2d-ae7036a6798b",
      "parameters": {
        "concept-set": {
          "description": "",
          "baseType": "OntologyObject"
        }
      }
    },

TODO: Remove this temporary list of API endpoints when done / if advisable
"""
import sys
from typing import Dict, List, Union

from requests import Response

from enclave_wrangler.config import ENCLAVE_PROJECT_NAME, TERMHUB_VERSION, VALIDATE_FIRST, config
from enclave_wrangler.objects_api import get_concept_set_version_expression_items, get_codeset_json
from enclave_wrangler.utils import enclave_get, make_actions_request, get_random_codeset_id  # set_auth_token_key,


UUID = str


def add_concepts_to_cset(omop_concepts: List[Dict], version__codeset_id: int, validate_first=VALIDATE_FIRST)-> List[Response]:
    """Wrapper function for routing to appropriate endpoint. Add existing OMOP concepts to a versioned concept set / codeset.

    :param omop_concepts (List[Dict]): A list of dictionaries.
      Each dictionary should have the following keys:
        - `concept_id` (int) (required)
        - `includeDescendants` (bool) (required)
        - `isExcluded` (bool) (required)
        - `includeMapped` (bool) (required)
        - `annotation` (str) (optional)
      Example:
        {
          "concept_id": 45259000,
          "includeDescendants": True,
          "isExcluded": False,
          "includeMapped": True,
          "annotation": "This is my concept annotation."
        }
     For additional information, refer to the documentation for the add_concepts_via_array(), i.e. docs for
     ...endpoint: add-selected-concepts-as-omop-version-expressions
    """
    # Group together all concepts that have the same settings
    keys_required = ['isExcluded', 'includeMapped', 'includeDescendants']
    keys_optional = ['annotation']
    omop_concept_groups: Dict[str, Dict] = {}
    for concept in omop_concepts:
        group_key_required = '__'.join([f'{k}_{v}' for k, v in concept.items() if k in keys_required])
        keys_optional_present = [k for k in keys_optional if k in concept]
        group_key_optional = '__'.join([f'{k}_{v}' for k, v in concept.items() if k in keys_optional_present])
        group_key = group_key_required + '__' + group_key_optional if group_key_optional else group_key_required
        keys = keys_required + keys_optional_present
        if group_key not in omop_concept_groups:
            omop_concept_groups[group_key] = {
                key: concept[key]
                for key in keys
            }
            omop_concept_groups[group_key]['omop_concept_ids'] = []
        omop_concept_groups[group_key]['omop_concept_ids'].append(concept)

    # Make calls for all grouped concepts
    responses: List[Response] = []
    for group in omop_concept_groups.values():
        response_i: Response = add_concepts_via_array(
            version=version__codeset_id,  # == code_sets.codeset_id
            concepts=[c['concept_id'] for c in group['omop_concept_ids']],
            is_excluded=group['isExcluded'],
            include_mapped=group['includeMapped'],
            include_descendants=group['includeDescendants'],
            optional_annotation=group['annotation'] if 'annotation' in group and  group['annotation'] else '',
            validate_first=validate_first)
        responses.append(response_i)

    return responses


# api_name = 'add-selected-concepts-as-omop-version-expressions'
def add_concepts_via_array(
    concepts: List[int], version: int, include_mapped: bool, include_descendants: bool, is_excluded: bool,
    optional_annotation: str = "", validate_first=VALIDATE_FIRST
) -> Response:
    """Create new concepts within concept set, AKA concept_set_version_items / expressions
    Non-required params set to `None`.

    :param version (int): Same as code_sets.codeset_id. When uploaded, can view here:
    - https://unite.nih.gov/workspace/data-integration/dataset/preview/ri.foundry.main.dataset.7104f18e-b37c-419b-9755-a732bfa33b03/master
    - https://unite.nih.gov/workspace/module/view/latest/ri.workshop.main.module.5a6c64c0-e82b-4cf8-ba5b-645cd77a1dbf
    """
    api_name = 'add-selected-concepts-as-omop-version-expressions'
    # Commented out portions are part of the api definition
    # Required params
    d = {
        # "apiName": "add-selected-concepts-as-omop-version-expressions",
        # "description": "",
        # "rid": "ri.actions.main.action-type.d1ad39f8-a303-4f46-8f46-bd48c5362915",
        "parameters": {
            "sourceApplication": 'TermHub',
              # "description": "",
              # "baseType": "String"
            "concepts": concepts,
              # "description": "",
              # "baseType": "Array<OntologyObject>"
            "includeMapped": include_mapped,
              # "description": "If true, then these expression items will match on the selected OMOP Concepts, and all of the Non-Standard OMOP Concepts that map to them. If Include Descendants is also true, then this option will also include all OMOP Concepts that map to the included descendants. Setting this to true enables you to include non-standard Concepts in your Concept Set. Mapping is the process to transform one Concept into a Standard one. Read more: ohdsi.github.io/TheBookOfOhdsi/Cohorts.html#conceptSets and https://www.ohdsi.org/web/wiki/doku.php?id=documentation:vocabulary:mapping",
              # "baseType": "Boolean"
            "includeDescendants": include_descendants,
              # "description": "If true, then these expression items will match on the selected OMOP Concepts, and all of their descendants.",
              # "baseType": "Boolean"
            # version: More docs in function docstring.
            "version": version,
              # "description": "",
              # "baseType": "OntologyObject"
            "isExcluded": is_excluded,
              # "description": "If true, then any concepts matched will be added to the expression as exclusion rather than inclusion criteria. Exclusion criteria take precedence over inclusion criteria, in cases when a single OMOP Concept is affected by more than one entry in the OMOP Concept Set Expression.",
              # "baseType": "Boolean"
            "optional-annotation": optional_annotation,
              # "description": "What are you trying to accomplish? Reason?",
              # "baseType": "String"
        }
    }

    # set_auth_token_key(personal=True)
    result = make_actions_request(api_name, d, validate_first)
    # set_auth_token_key(personal=False)
    return result


# api_name = 'set-omop-concept-set-version-item'
# TODO: Considering removing this function to this endpoint, as can't pass the codeset_id / verion_id, and not sure
#  if we will find useful at all.
# noinspection PyUnusedLocal
def update_concept_version_item(        # TODO: delete? not being used currently
    include_descendants: bool, concept_set_version_item: str, is_excluded: bool, include_mapped: bool, validate_first=VALIDATE_FIRST
)-> Response:
    """Create new concepets within concept set

    This endpoint: in concept set editor w/ existing expression item, can click on it and change one of those flags to
    different value. It just changes the values.

    :param concept_set_version_item (str): todo: What to put here? OMOP concept_id? (item_id is a random uuid)

    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
        https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/set-omop-concept-set-version-item/validate \
        --data '{"parameters":{"include_descendants":false }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"
    """
    api_name = 'set-omop-concept-set-version-item'
    # Commented out portions are part of the api definition
    d = {
        # "apiName": "set-omop-concept-set-version-item",
        # "description": "",
        # "rid": "ri.actions.main.action-type.56ce9a5b-c535-4413-be70-5526a8c152ed",
        # - Required params
        "parameters": {
            "include_descendants": include_descendants,
            # "include_descendants": {
            #   "description": "",
            #   "baseType": "Boolean"
            "concept-set-version-item": concept_set_version_item,
            # concept-set-version-item: More docs in function docstring.
            # TODO: is this supposed to be OMOP concept_id? (I think it's something else; expression have own id?)
            # "concept-set-version-item": {
            #   "description": "",
            #   "baseType": "OntologyObject"
            # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.
            "is_excluded": is_excluded,
            # "is_excluded": {
            #   "description": "",
            #   "baseType": "Boolean"
            "include_mapped": include_mapped,
            # "include_mapped": {
            #   "description": "",
            #   "baseType": "Boolean"
        }
    }
    return make_actions_request(api_name, d, validate_first)


# api_name = 'edit-omop-concept-set-version-item'
# TODO: Ask Amin: Is this alternative to 'add-selected-concepts-as-omop-version-expressions' (add_concepts_via_array())?
#  ...that is, does it do the same thing as passing an array of size 1 to that endpoint? If not, what's different?
#  ...If it indeed is the same, then I imagine for OmopConceptSetVersionItem I want to pass an OMOP concept_id? Or?
#   @jflack4: yeah, this is for a single version item and requires the version item identifier --
#             not sure if we would use it. I think it's for editing version items already added while
#             editing draft cset versions in the concept set editor
def add_concept_via_edit(
    OmopConceptSetVersionItem: str, version: int, include_descendants=False, is_excluded=False, include_mapped=False,
    validate_first=VALIDATE_FIRST
)-> Response:
    """Create new concepets within concept set
    Non-required params set to `None`.
    """
    api_name = 'edit-omop-concept-set-version-item'
    d = {
        # "apiName": "edit-omop-concept-set-version-item",
        # "description": "",
        # "rid": "ri.actions.main.action-type.be264050-8b7f-44fe-9082-5fb4b748049a",
        "parameters": {
            "include_descendants": include_descendants,
              # "description": "If true, then these expression items will match on the selected OMOP Concepts, and all of their descendants.",
              # "baseType": "Boolean"
            "is_excluded": is_excluded,
              # "description": "If true, then any concepts matched will be added to the expression as exclusion rather than inclusion criteria. Exclusion criteria take precedence over inclusion criteria, in cases when a single OMOP Concept is affected by more than one entry in the OMOP Concept Set Expression.",
              # "baseType": "Boolean"
            "OmopConceptSetVersionItem": OmopConceptSetVersionItem,
              # "description": "",
              # "baseType": "OntologyObject"
            # version: More docs in function docstring.
            "version": version,
              # "description": "",
              # "baseType": "OntologyObject"
            "include_mapped": include_mapped,
              # "description": "If true, then these expression items will match on the selected OMOP Concepts, and all of the Non-Standard OMOP Concepts that map to them. If Include Descendants is also true, then this option will also include all OMOP Concepts that map to the included descendants. Setting this to true enables you to include non-standard Concepts in your Concept Set. Mapping is the process to transform one Concept into a Standard one. Read more: ohdsi.github.io/TheBookOfOhdsi/Cohorts.html#conceptSets and https://www.ohdsi.org/web/wiki/doku.php?id=documentation:vocabulary:mapping",
              # "baseType": "Boolean"
        }
    }
    return make_actions_request(api_name, d, validate_first)


# code_set
# TODO: strange that new-parameter and new-parameter1 are required. I added arbitrary strings
def upload_concept_set_version_draft(
    concept_set: str = None, base_version: int = None, current_max_version: float = None, version_id: int = None,
    on_behalf_of: str = None, intention: str = None, domain_team: str = None, provenance: str = None,
    annotation: str = None, limitations: str = None, intended_research_project: str = None, authority: str = None,
    copyExpressionsFromBaseVersion: bool = False, validate_first=VALIDATE_FIRST
)-> Response:
    """Create a new draft concept set version.

    :param domain_team (str): todo: domain_team: Not sure what to put here, but it is optional param, so I'm leaving blank - Joe
    :param annotation (str): todo: annotation: this should be moved into the new palantir-3-file data model, whatever that is - Joe
    :param intended_research_project (str): todo: intended_research_project: (a) default this to ENCLAVE_PROJECT_NAME in func, (b) do that here, (c) add it as a column to an updated palantir-3-file for the new api - Joe
    :param authority (str): todo: authority: Not sure what to put here, but it is optional param, so I'm leaving blank - Joe
    :param current_max_version (float): todo: current-max-version: Is it usefull to pass this? Is there any way to do a GET against the concept set container (name / ID) to find this out? Or would we have to track these versions in a local registry? - Joe
    :param base_version (int): # todo: base_version: Is it useful to pass this? how to know this? Depends on current-max-version as well. - Joe
    :param version_id (int): Equal to code_sets.codeset_id:
    https://unite.nih.gov/workspace/data-integration/dataset/preview/ri.foundry.main.dataset.7104f18e-b37c-419b-9755-a732bfa33b03/master

    Non-required params set to `None`.

    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/create-new-draft-omop-concept-set-version/validate \
            --data '{"parameters":{"domain-team":"just for testing of action api by Siggie" }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"

    """
    api_name = 'create-new-draft-omop-concept-set-version'

    # Validate / warnings
    current_max_version_docstring = \
        "`current_max_version`: This must be set to the current maximum version number assigned to a version of this " \
        "concept set, or null if creating the first version of a concept set. If null, then baseVersion is not required"
    current_max_version_shared_warning_msg = \
        f'Attempting to upload, though if there is an error, this may be the cause. Original documentation for ' \
        f'`current_max_version`\n: {current_max_version_docstring}'
    if version_id == 0 and current_max_version:  # was version_id <= 1, which errored if version_id=None
        print(f'Warning: `version_id` {version_id} appears to be first version, in which case `current_max_version`'
              f' should be `null` (`None` in Python). You passed {current_max_version} for `current_max_version`.\n'
              f'{current_max_version_shared_warning_msg}', file=sys.stderr)
    if base_version and not current_max_version:
        print(f'Warning: You passed a `base_version`, which is not required when there is no `current_max_version`.', file=sys.stderr)

    # TODO: @jflack4...this needs to change but seems like it was left in the middle, not sure what to
    #       do with it, but trying to accept base_version in place of conceptSet. see comments
    #       in dataset_upload.py:upload_new_cset_version_with_concepts_from_csv()

    # Commented out portions are part of the api definition
    d = {
        # "apiName": api_name,
        # "description": "",
        # "rid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
        # - Required params
        "parameters": {
            "sourceApplication": 'TermHub',
            # "description": "",
            # "baseType": "String"
            "sourceApplicationVersion": TERMHUB_VERSION,
            # "description": "",
            # "baseType": "String"
            "conceptSet": concept_set,
            # "conceptSet": {
            #   "description": "",
            #   "baseType": "OntologyObject"
            # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.

            "intention": intention,
            # "intention": {
            #   "description": "",
            #   "baseType": "String"
            # - validation info: Ideally one of the following, though other values are accepted:
            #   "Broad (sensitive)", "Narrow (specific)", "Mixed"
            "copyExpressionsFromBaseVersion": copyExpressionsFromBaseVersion,
        }
    }

    # - Optional params
    # "domain-team": {
    #   "description": "",
    #   "baseType": "OntologyObject"
    # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.
    # todo: more info in function docstring
    if domain_team:
        d['parameters']['domain-team'] = domain_team

    # "provenance": {
    #   "description": "This field is optional, you will have a chance to fill this in later.",
    #   "baseType": "String"
    if provenance:
        d['parameters']['provenance'] = provenance

    # "current-max-version": {
    #   "description": "This must be set to the current maximum version number assigned to a version of this "
    #     "concept set, or null if creating the first version of a concept set. If null, then baseVersion is not "
    #     "required",
    #   "baseType": "Double"
    # todo: more info in function docstring
    if current_max_version:
        d['parameters']['current-max-version'] = current_max_version

    # "annotation": {
    #   "description": "",
    #   "baseType": "String"
    # todo: more info in function docstring
    if annotation:
        d['parameters']['annotation'] = annotation

    # "limitations": {
    #   "description": "This field is optional, you will have a chance to fill this in later.",
    #   "baseType": "String"
    if limitations:
        d['parameters']['limitations'] = limitations

    # "baseVersion": {
    #   "description": "",
    #   "baseType": "OntologyObject"
    # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.
    # todo: more info in function docstring
    if base_version:
        d['parameters']['baseVersion'] = base_version

    # "intended-research-project": {
    #   "description": "",
    #   "baseType": "OntologyObject"
    # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.
    # todo: more info in function docstring
    if intended_research_project:
        d['parameters']['intended-research-project'] = intended_research_project

    # "versionId": {
    #   "description": "",
    #   "baseType": "Integer"
    if version_id:  # == code_sets.codeset_id
        d['parameters']['versionId'] = version_id

    # "authority": {
    #   "description": "",
    #   "baseType": "String"
    # todo: more info in function docstring
    if authority:
        d['parameters']['authority'] = authority

    if on_behalf_of:
        d['parameters']['on-behalf-of'] = on_behalf_of
    else:
        raise "expecting 'on_behalf_of'"

    response: Response = make_actions_request(api_name, d, validate_first)
    if 'errorCode' in response:
        print(response, file=sys.stderr)
        # todo: What can I add to help the user figure out what to do to fix, until API returns better responses?

    return response


def finalize_concept_set_version(
    concept_set: str, version_id: int, on_behalf_of: str, current_max_version: float, provenance: str = "",
    limitations: str = "", validate_first=VALIDATE_FIRST
)-> Response:
    """Finalize a concept set version

    # todo: add docs for params & curl example
    :param version_id (int): Equal to code_sets.codeset_id:
    https://unite.nih.gov/workspace/data-integration/dataset/preview/ri.foundry.main.dataset.7104f18e-b37c-419b-9755-a732bfa33b03/master

    Non-required params set to `None`.
    """
    api_name = 'finalize-draft-omop-concept-set-version'

    # Commented out portions are part of the api definition
    d = {
        # "apiName": api_name,
        # "description": "",
        # "rid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
        # - Required params
        "parameters": {
            "new-parameter": limitations,  # required
            #   "description": "",
            #   "baseType": "String"
            "new-parameter1": provenance,  # required
            #   "description": "",
            #   "baseType": "String"

            # not sure what the hell happened to the r in the api container parameter
            # "concept-set-container": concept_set,
            "concept-set-containe": concept_set,
            # "description": "",
            # "baseType": "OntologyObject"
            # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already
            #   existing in enclave.

            "version": version_id,
            # "description": "",
            # "baseType": "OntologyObject"
            "currentMaxVersion": current_max_version,
            #   "description": "",
            #   "baseType": "Double"
        }
    }
    if on_behalf_of:
        d['parameters']['on-behalf-of'] = on_behalf_of
    else:
        raise "expecting 'on_behalf_of'"

    response: Response = make_actions_request(api_name, d, validate_first)
    if 'errorCode' in response:
        print(response, file=sys.stderr)
        # todo: What can I add to help the user figure out what to do to fix, until API returns better responses?

    return response


# concept_set_container
def upload_concept_set_container(
    on_behalf_of: str, concept_set_id: str, intention: str, research_project: ENCLAVE_PROJECT_NAME,
    assigned_sme: str = None, assigned_informatician: str = None, validate_first=VALIDATE_FIRST,
)-> Response:
    """Create a new concept set
    Non-required params set to `None`.

    :param concept_set_id (str) (required):
    :param intention (str) (required):
    :param research_project (str) (required): todo: add it as a column to an updated palantir-3-file
    :param assigned_sme (str) (optional):
    :param assigned_informatician (str) (optional):

    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/create-new-concept-set/validate \
            --data '{"parameters":{"intention":"just for testing of action api by Siggie" }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"
    """
    api_name = 'create-new-concept-set'
    # Commented out portions are part of the api definition
    d = {
        # "apiName": api_name,
        # "description": "Creates a new 'empty' Concept Set linked to a research project",
        # "rid": "ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae",
        "parameters": {
            # - Required params
            "on-behalf-of": on_behalf_of,
            "concept_set_id": concept_set_id,
            # "concept_set_id": {
            #     "description": "",
            #     "baseType": "String"
            "status": "Under Construction",
            # "status": {
            #     "description": "",
            #     "baseType": "String"
            # - validation info: oneOf: "Under Construction" (only allows for this value)
            "intention": intention,
            # "intention": {
            #     "description": "",
            #     "baseType": "String"
            # - validation info: Ideally one of the following, though other values are accepted:
            #   "Broad (sensitive)", "Narrow (specific)", "Mixed"
            "research-project": research_project,
            # "research-project": {
            #     "description": "Research project Concept Set is being created for",
            #     "baseType": "OntologyObject"
            # - validation info: Needs to be a valid reference (objectQueryResult) to object/property/value already existing in enclave.
            "stage": "Awaiting Editing",
            # "stage": {
            #     "description": "",
            #     "baseType": "String"
            # - validation info: oneOf: "Awaiting Editing" (only allows for this value)
        }
    }
    # - Optional params
    # "assigned_sme": {
    #     "description": "",
    #     "baseType": "String"
    # - validation info: Needs to be a valid reference (groupMember) to object/property/value already existing in enclave.
    if assigned_sme:
        d['parameters']['assigned_sme'] = assigned_sme

    # "assigned_informatician": {
    #     "description": "",
    #     "baseType": "String"
    # - validation info: Needs to be a valid reference (groupMember) to object/property/value already existing in enclave.
    if assigned_informatician:
        d['parameters']['assigned_informatician'] = assigned_informatician

    # try:
    response: Response = make_actions_request(api_name, d, validate_first)
    # except Exception as e:
    #     print(e)
    if 'errorCode' in response:
        print(response, file=sys.stderr)
        print('If above error message does not say what is wrong, it is probably the case that the `concept_set_id` '
              f'already exists. You passed: {concept_set_id}')
    return response


def delete_concept_set_version(version_id: int, validate_first=VALIDATE_FIRST) -> Response:
    """Delete a concept set version --- DRAFTS only, can't delete completed versions

    Cavaets:
    1. Amin said `isMostRecentVersion` note in API definition here does not matter for our use case, or it is not a
      correct warning.
    2. We need to add `expression-items` because enclave isn't set up to clear orphan expression items when version
      is deleted, so we need to ask to delete them manually.
    3. If `version_id` is not available because we did not pre-assign before uploading new version, we don't at the
      moment know how to get it. So best if we pre-assign. - Joe 2022/12/12
    4. `omop-concept-set` is not for the container name, but the version ID.

    """
    api_name = 'delete-omop-concept-set-version'
    expression_items: List[UUID] = get_concept_set_version_expression_items(version_id, return_detail='id')
    # todo?: Expression items not reliably showing up after version just created: I don't know if this will be reliable
    #  100% of the time. at first... i was getting no expression items back after just creating it and trying to delete.
    #  i checked the enclave, and I saw that the version did indeed have expression items. I take this to mean that
    #  there is some delay before the API can fetch these items. So maybe if wea `wait`, that might fix the problem.
    #  For now, immediately calling it again works. - Joe 2022/12/12
    if not expression_items:
        print('INFO: Could not find expression items while trying to delete concept set. '
              'This probably means it was just uploaded. Trying again.')
        expression_items: List[UUID] = get_concept_set_version_expression_items(version_id, return_detail='id')
    # Note: Ignore 'description' below. See 'cavaet 1' in this function's docstring.
    d = {
        # "apiName": api_name,
        # "description": "Do not forget to the flag 'Is Most Recent Version' of the previous Concept Set Version",
        # "rid": "ri.actions.main.action-type.93b82f88-bd55-4daf-a0f9-f6537bf2bce1",
        "parameters": {
            # - Required params
            "omop-concept-set": version_id,
            # "omop-concept-set": {
            #     "description": "",
            #     "baseType": "OntologyObject"
            "expression-items": expression_items,
            # "expression-items": {
            #     "description": "",
            #     "baseType": "Array<OntologyObject>"
        }
    }
    # TODO: Solve: requests.exceptions.HTTPError: 400 Client Error: Bad Request for url: https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/delete-omop-concept-set-version/apply
    #  - Joe: I sent Siggie the curl for this unit test request on 2022/12/12
    response: Response = make_actions_request(api_name, d, validate_first)
    return response


def get_action_types() -> Response:
    """Get action types / API action endpoint definitions
    curl -H "Authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN " \
    "https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actionTypes"
    https://unite.nih.gov/docs/foundry/api/ontology-resources/action-types/list-action-types/
    """
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/actionTypes'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    response: Response = enclave_get(url)
    return response.json()['data']


if __name__ == '__main__':
    concept_set_name = 'ag - test'
    parent_codeset_id = 147725421
    current_max_version = 4.0
    concept_id_to_delete = 2108681 # Patient receiving care in the intensive care unit (ICU) and receiving mechanical ventilation, 24 hours or less (CRIT)
    test_draft_codeset_id = get_random_codeset_id()
    print(f'creating test cset version: {test_draft_codeset_id}')
    result = upload_concept_set_version_draft(  # upload_new_cset_version_with_concepts(  # upload_concept_set_version
        concept_set=concept_set_name, base_version=parent_codeset_id, current_max_version=current_max_version,
        version_id=test_draft_codeset_id, copyExpressionsFromBaseVersion=True,
        on_behalf_of='5c560c3e-8e55-485c-9a66-f96285f273a0', intended_research_project='RP-4A9E27',
        intention='Testing version upload', provenance='Nowhere', limitations='Total',
        validate_first=True) # left out domain_team:str, annotation:str, authority:str
    print(result)
    from enclave_wrangler.utils import make_objects_request, EnclaveWranglerErr
    item = make_objects_request(
        f'objects/OMOPConceptSet/{test_draft_codeset_id}/links/OmopConceptSetVersionItem?p.conceptId.eq={concept_id_to_delete}',
        verbose=True, retry_if_empty=True, return_type='data')
    if len(item) != 1:
        raise EnclaveWranglerErr("unexpected return from make_objects_request")
    item = item[0]
    print(item)
    # csets = get_objects_df('OMOPConceptSet')
    itemId = item['properties']['itemId']

    j = get_codeset_json(test_draft_codeset_id)

    result = make_actions_request(
        api_name='discard-omop-concept-set-expression',
        data= {
            "parameters": {
                "concept-set-version-item": [f"{itemId}"],
                "version": test_draft_codeset_id
            }
        },
    )
    print(item)
    print('delete draft now')
    response = delete_concept_set_version(test_draft_codeset_id)
    print(response)

# concept_set_name: str, parent_version_codeset_id: int, current_max_version: float, omop_concepts: List[Dict],
# provenance: str = "", limitations: str = "", intention: str = "", annotation: str = "",
# intended_research_project: str = None, on_behalf_of: str = None, codeset_id: int = None, \
# validate_first=VALIDATE_FIRST, finalize=True # maybe finalize should default to False?
