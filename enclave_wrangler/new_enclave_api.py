"""New Enclave API

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

import requests

from enclave_wrangler.config import config


JSON_TYPE = Union[List, Dict]


def upload_concept(
    include_descendants: bool, concept_set_version_item: str, is_excluded: bool, include_mapped: bool, validate=False
) -> JSON_TYPE:
    """Create new concepets within concept set
    Non-required params set to `None`.
    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
        https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/set-omop-concept-set-version-item/validate \
        --data '{"parameters":{"include_descendants":false }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"

# todo: remove this when no longer needed for reference:
{
  "result": "INVALID",
  "submissionCriteria": [
    {
      "result": "INVALID",
      "configuredFailureMessage": "Condition not met"
    }
  ],
  "parameters": {
    "include_descendants": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": true
    },
    "is_excluded": {
      "result": "INVALID",
      "evaluatedConstraints": [],
      "required": true
    },
    "concept-set-version-item": {
      "result": "INVALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": true
    },
    "include_mapped": {
      "result": "INVALID",
      "evaluatedConstraints": [],
      "required": true
    }
  }
}
    """
    api_name = 'set-omop-concept-set-version-item'
    # Commented out portions are part of the api definition
    d = {
        # "apiName": "set-omop-concept-set-version-item",
        # "description": "",
        # "rid": "ri.actions.main.action-type.56ce9a5b-c535-4413-be70-5526a8c152ed",
        # TODO: Fix commented out fields 1 at a time. getting errors 400/500, so idk what's wrong yet
        # - Required params
        "parameters": {
            "include_descendants": include_descendants,
            # "include_descendants": {
            #   "description": "",
            #   "baseType": "Boolean"
            "concept-set-version-item": concept_set_version_item,
            # "concept-set-version-item": {
            #   "description": "",
            #   "baseType": "OntologyObject"
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
    return post(api_name, d, validate)


def upload_draft_concept_set(
    domain_team: str, provenance: str, current_max_version: float, concept_set: str, annotation: str, limitations: str,
    intention: str, base_version: int, intended_research_project: str, version_id: int, authority: str, validate=False
) -> JSON_TYPE:
    """Create a new draft concept set
    Non-required params set to `None`.
    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/create-new-draft-omop-concept-set-version/validate \
            --data '{"parameters":{"domain-team":"just for testing of action api by Siggie" }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"

# todo: remove this when no longer needed for reference:
{
  "result": "INVALID",
  "submissionCriteria": [],
  "parameters": {
    "domain-team": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": false
    },
    "provenance": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    },
    "current-max-version": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    },
    "conceptSet": {
      "result": "INVALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": true
    },
    "annotation": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    },
    "limitations": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    },
    "intention": {
      "result": "INVALID",
      "evaluatedConstraints": [
        {
          "type": "oneOf",
          "options": [
            {
              "displayName": "",
              "value": "Broad (sensitive)"
            },
            {
              "displayName": "",
              "value": "Narrow (specific)"
            },
            {
              "displayName": "",
              "value": "Mixed"
            }
          ],
          "otherValuesAllowed": true
        }
      ],
      "required": true
    },
    "baseVersion": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": false
    },
    "intended-research-project": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": false
    },
    "versionId": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    },
    "authority": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": false
    }
  }
}
    """
    api_name = 'create-new-draft-omop-concept-set-version'
    # Commented out portions are part of the api definition
    d = {
        # "apiName": api_name,
        # "description": "",
        # "rid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
        # - Required params
        "parameters": {
            # TODO: Fix commented out fields 1 at a time. getting errors 400/500/422/404, so idk what's wrong yet
            # "conceptSet": concept_set,
            # # "conceptSet": {
            # #   "description": "",
            # #   "baseType": "OntologyObject"
            # # conceptSet: Validate shows:
            # #   "evaluatedConstraints": [{"type": "objectQueryResult"}],

            "intention": intention,
            # "intention": {
            #   "description": "",
            #   "baseType": "String"
        }
    }
    # - Optional params
    # "domain-team": {
    #   "description": "",
    #   "baseType": "OntologyObject"
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
    if current_max_version:
        d['parameters']['current-max-version'] = current_max_version

    # "annotation": {
    #   "description": "",
    #   "baseType": "String"
    if annotation:
        d['parameters']['annotation'] = annotation

    # "limitations": {
    #   "description": "This field is optional, you will have a chance to fill this in later.",
    #   "baseType": "String"
    if limitations:
        d['parameters']['limitations'] = limitations

    # TODO: Fix commented out fields 1 at a time. getting errors 400/500/422/404, so idk what's wrong yet
    # "baseVersion": {
    #   "description": "",
    #   "baseType": "OntologyObject"
    if base_version:
        d['parameters']['baseVersion'] = base_version

    # "intended-research-project": {
    #   "description": "",
    #   "baseType": "OntologyObject"
    if intended_research_project:
        d['parameters']['intended-research-project'] = intended_research_project

    # "versionId": {
    #   "description": "",
    #   "baseType": "Integer"
    if version_id:
        d['parameters']['versionId'] = version_id

    # "authority": {
    #   "description": "",
    #   "baseType": "String"
    if authority:
        d['parameters']['authority'] = authority

    return post(api_name, d, validate)


# TODO: Failure: test_upload_concept_set {'errorCode': 'INVALID_ARGUMENT', 'errorName': 'InvalidUserId', 'errorInstanceId': '8ee43d3a-39d5-40a9-b868-12f768ba5f50', 'parameters': {'userId': 'x'}}
def upload_concept_set(
    concept_set_id: str, intention: str, research_project: str, assigned_sme: str = None,
    assigned_informatician: str = None, validate=False
) -> JSON_TYPE:
    """Create a new concept set
    Non-required params set to `None`.
    Example curl:
        curl -H "Content-type: application/json" -H "Authorization: Bearer $OTHER_TOKEN" \
            https://unite.nih.gov/api/v1/ontologies/ri.ontology.main.ontology.00000000-0000-0000-0000-000000000000/actions/create-new-concept-set/validate \
            --data '{"parameters":{"intention":"just for testing of action api by Siggie" }}' | jq
        - Validate: Use above CURL
        - Apply: (replace /validate with /apply in above string)
        - This is a sign that it worked: "curl: (52) Empty reply from server"

# todo: remove this when no longer needed for reference:
{
  "result": "VALID",
  "submissionCriteria": [],
  "parameters": {
    "assigned_sme": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "groupMember"
        }
      ],
      "required": false
    },
    "assigned_informatician": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "groupMember"
        }
      ],
      "required": false
    },
    "concept_set_id": {
      "result": "VALID",
      "evaluatedConstraints": [],
      "required": true
    },
    "intention": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "oneOf",
          "options": [
            {
              "displayName": "",
              "value": "Broad (sensitive)"
            },
            {
              "displayName": "",
              "value": "Narrow (specific)"
            },
            {
              "displayName": "",
              "value": "Mixed"
            }
          ],
          "otherValuesAllowed": true
        }
      ],
      "required": true
    },
    "research-project": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "objectQueryResult"
        }
      ],
      "required": true
    },
    "status": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "oneOf",
          "options": [
            {
              "displayName": "",
              "value": "Under Construction"
            }
          ],
          "otherValuesAllowed": false
        }
      ],
      "required": true
    },
    "stage": {
      "result": "VALID",
      "evaluatedConstraints": [
        {
          "type": "oneOf",
          "options": [
            {
              "displayName": "",
              "value": "Awaiting Editing"
            }
          ],
          "otherValuesAllowed": false
        }
      ],
      "required": true
    }
  }
}
    """
    api_name = 'create-new-concept-set'
    # Commented out portions are part of the api definition
    d = {
        # "apiName": api_name,
        # "description": "Creates a new 'empty' Concept Set linked to a research project",
        # "rid": "ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae",
        "parameters": {
            # - Required params
            "concept_set_id": concept_set_id,
            # "concept_set_id": {
            #     "description": "",
            #     "baseType": "String"
            "status": "Under Construction",
            # status: As of 2022/10/19, only 'Under Construction' is allowed
            # "status": {
            #     "description": "",
            #     "baseType": "String"
            "intention": intention,
            # "intention": {
            #     "description": "",
            #     "baseType": "String"
            "research-project": research_project,
            # "research-project": {
            #     "description": "Research project Concept Set is being created for",
            #     "baseType": "OntologyObject"
            "stage": "Awaiting Editing",
            # stage: As of 2022/10/19, only 'Awaiting Editing' is allowed
            # "stage": {
            #     "description": "",
            #     "baseType": "String"
        }
    }
    # - Optional params
    # "assigned_sme": {
    #     "description": "",
    #     "baseType": "String"
    if assigned_sme:
        d['parameters']['assigned_sme'] = assigned_sme
    # "assigned_informatician": {
    #     "description": "",
    #     "baseType": "String"
    if assigned_informatician:
        d['parameters']['assigned_informatician'] = assigned_informatician

    return post(api_name, d, validate)


def make_request(api_name: str, data: Union[List, Dict] = None, validate=False, verbose=False) -> JSON_TYPE:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        # todo: When/if @Amin et al allow enclave service token to write to the new API, change this back from.
        # "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
        "authorization": f"Bearer {config['OTHER_TOKEN']}",
        "Content-type": "application/json",

    }
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/actions/{api_name}/'
    api_path += 'validate' if validate else 'apply'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    if verbose:
        print(f'make_request: {api_path}\n{url}')

    try:
        if data:
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)
        response.raise_for_status()
    except BaseException as err:
        print(f"Unexpected {type(err)}: {str(err)}", file=sys.stderr)

    # noinspection PyUnboundLocalVariable
    response_json: JSON_TYPE = response.json()
    return response_json


def get(api_name: str, validate=False) -> JSON_TYPE:
    """For GET request"""
    return make_request(api_name, validate=validate)


def post(api_name: str, data: Dict, validate=False) -> JSON_TYPE:
    """For POST request"""
    return make_request(api_name, data, validate)
