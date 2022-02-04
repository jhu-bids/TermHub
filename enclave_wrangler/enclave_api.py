"""BulkImport VSAC Concept Sets and import them into the N3C Enclave using the API
## APIs need to be called in the following order:
## 1. Create new concept set container
## 2. Create new draft version  -
## Note, new draft version id must be generated within the range of 1,000,000,000, 1,001,000,000.
## and used to add the CodeSystemExpressionItems
## 3. Create CodeSystemExpression items - TBD

Resources
- Validate URL (for testing POSTs without it actually taking effect): https://unite.nih.gov/actions/api/actions/validate
- Wiki article on how to create these JSON: https://github.com/National-COVID-Cohort-Collaborative/Data-Ingestion-and-Harmonization/wiki/BulkImportConceptSet-REST-APIs
"""
from typing import Any, Dict, List, Union

import requests
import json
from enclave_wrangler.utils import log_debug_info

DEBUG = True

def post_request_enclave_api(api_url: str, header: Dict, data: Dict):
    response = requests.post(api_url, data=json.dumps(data), headers=header)
    response_json = response.json()
    if DEBUG:
        log_debug_info()
        print(response_json)  # temp
    if 'type' not in response_json or response_json['type'] != 'validResponse':
        raise SystemError(json.dumps(response_json, indent=2))

    return response_json


## 1/3. Create new concept set container (concept_set_container_edited.csv)
# - 1 call per container
#post request to call create the concept set container
# CreateNewConceptSet rid =ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae
#1. header should contain the authentication bearer token
#2. set actionTypeRid for the createNewConceptSet in the data
#3. set all parameter types and values in the data
# Example, data = { “actionTypeRid”: “ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae”,
# for creating a new concept set container, need to set following parameters:
# concept set name, intention, assigned informatician, assigned SME, status, stage, and Research Project
# creatNewConceptSet
# ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae
# concept set name (string) : ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807
# intention (string) : ri.actions.main.parameter.9e33b4d9-c7eb-4f27-81cd-152cc89f334b
# assigned information (string):  ri.actions.main.parameter.28448734-2b6c-41e7-94aa-9f0d2ac1936f
# assigned sme (string) : ri.actions.main.parameter.f04fd21f-4c97-4640-84e3-f7ecff9d1018
# status (string whose value is always "Under Construction") : ri.actions.main.parameter.2b3e7cd9-6704-40a0-9383-b6c734032eb3
# stage (string whose value is always "Awaiting Editing"): ri.actions.main.parameter.02dbf67e-0acc-43bf-a0a9-cc8d1007771b
# Research Project (object) : ri.actions.main.parameter.a3eace19-c42d-4ff5-aa63-b515f3f79bdd
## concept_set_name
def get_cs_container_data(cs_name: str) -> Dict:
    cs_container_data = {
        "actionTypeRid": "ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae",
        "parameters": {
            "ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807": {
                "type": "string",
                "string": cs_name
            },
            "ri.actions.main.parameter.28448734-2b6c-41e7-94aa-9f0d2ac1936f": {
                #informatician
                "type": "string",
                "string": "a39723f3-dc9c-48ce-90ff-06891c29114f"
            },
            "ri.actions.main.parameter.f04fd21f-4c97-4640-84e3-f7ecff9d1018": {
                "null": {},
                "type": "null"
            }, # sme
            "ri.actions.main.parameter.2b3e7cd9-6704-40a0-9383-b6c734032eb3": {
                "string": "Under Construction",
                "type": "string"
            },
            "ri.actions.main.parameter.02dbf67e-0acc-43bf-a0a9-cc8d1007771b": {
                "string": "Awaiting Editing",
                "type": "string"
            },
            "ri.actions.main.parameter.9e33b4d9-c7eb-4f27-81cd-152cc89f334b": {
                "string": "Mixed",
                "type": "string"
            },
            "ri.actions.main.parameter.a3eace19-c42d-4ff5-aa63-b515f3f79bdd": {
                    "objectLocator": {
                        "objectTypeId": "research-project", "primaryKey": {
                            "research_project_uid": {
                                "string": "RP-4A9E27",
                                "type": "string"
                            }
                        }
                    }, "type": "objectLocator"}}}
    return cs_container_data

## # cs_name, cs_id, intension, limitation, update_msg, status, provenance
## TODO: utilize: cs_name, cs_id
def get_cs_version_data(cs_name, cs_id, intention, limitations, update_msg, provenance):
    """This code will be used to pass to 'action' endpoint, then it passes to this TypeScript function
    which will create a modified object, pass it back to 'action', and 'action' will make the actual change:
    https://unite.nih.gov/workspace/data-integration/code/repos/ri.stemma.main.repository.f4a40537-2187-46f4-ae90-c54ca36eb0c2/contents/f6a597efe3/functions-typescript/src/editor.ts
    """

    # Temp: Leaving this here for now as a static example of an attempt that actually worked today. - Joe 2022/02/02
#     return {
#     "actionTypeRid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
#     "parameters": {
#         "ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971": {
#             "null": {},
#             "type": "null"
#         },
#         "ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8": {
#             "objectLocator": {
#                 "objectTypeId": "omop-concept-set-container",
#                 "primaryKey": {
#                     "concept_set_id": {
#                         "string": "stephanie test cs",
#                         "type": "string"
#                     }
#                 }
#             },
#             "type": "objectLocator"
#         },
#         "ri.actions.main.parameter.465404ad-c767-4d73-ab26-0d6e083eab8e": {
#             "objectLocator": {
#                 "objectTypeId": "research-project",
#                 "primaryKey": {
#                     "research_project_uid": {
#                         "string": "RP-4A9E27",
#                         "type": "string"
#                     }
#                 }
#             },
#             "type": "objectLocator"
#         },
#         "ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13": {
#             "null": {},
#             "type": "null"
#         },
#         "ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e60324074661": {
#             "string": "upd",
#             "type": "string"
#         },
#         "ri.actions.main.parameter.4e790085-47ed-41ad-b12e-72439b645031": {
#             "null": {},
#             "type": "null"
#         },
#         "ri.actions.main.parameter.5577422c-02a4-454a-97d0-3fb76425ba8c": {
#             "null": {},
#             "type": "null"
#         },
#         "ri.actions.main.parameter.2d5df665-6728-4f6e-83e5-8256551f8851": {
#             "type": "string",
#             "string": "Broad (sensitive)"
#         },
#         "ri.actions.main.parameter.32d1ce35-0bc1-4935-ad18-ba4a45e8113f": {
#             "null": {},
#             "type": "null"
#         },
#         "ri.actions.main.parameter.eac89354-a3bf-465e-a4be-bbf22a6e2c50": {
#             "null": {},
#             "type": "null"
#         }
#     }
# }

    # TODO: We should add a quality control check:
    #  If any of the values passed are null/None, need to do "type": "null" and "null": {} instead of  e.g. "string"
    #  ...Amin said this is only needed for optional params.
    cs_version_data = {
        "actionTypeRid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
        "parameters": {
            # ID: range(1billion, 1.1billion; non-inclusive) (optional)
            # TODO: We had success by nullifying this. Amin told us that our integer ID looks good,
            #  ...but they're still seeing an error on their end, so he's looking into it. - Joe 2022/02/02
            "ri.actions.main.parameter.eac89354-a3bf-465e-a4be-bbf22a6e2c50": {
                # "type": "integer",
                # "integer ": 1000000001
                "type": "null",
                "null": {}
            },  # reserved id list from DI&H id bank, cannot be reused
            # TODO: does "stephanie cs example" match an actual container?

            "ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8": {
                "type": "objectLocator",
                "objectLocator": {
                    "objectTypeId": "omop-concept-set-container",
                    "primaryKey": {
                        "concept_set_id": {
                            "type": "string",
                            # Amin asked us to use this instead:
                            # "string": "stephanie cs example"
                            "string": "stephanie test cs"
                        }
                    }
                }
            },  # cs_name must match the string from the container
            # Current maximum version (deprecated):
            # - In the ConceptSetEditor GUI, maximum version is passed in. But in the case where
            # ...we're creating the first version, this can be null.
            "ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13": {
                "null": {},
                "type": "null"
                # "double": 0,
                # "type": "double"
            },
            # Actual object concept version (starting from) (optional):
            # - Logic is that you might create a new version. This is the parent version.
            # - If "current max version" is null, this needs to be null. This param is required to be non-null if
            # ...and only if "current max version" is not null.
            "ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971": {
                "null": {},
                "type": "null"
            },
            # Update message (optional; deprecated):
            "ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e60324074661": {
                "type": "string",
                "string": update_msg
            },
            # Intention:
            "ri.actions.main.parameter.2d5df665-6728-4f6e-83e5-8256551f8851": {
                "type": "string",
                "string": intention
            },
            # Limitations:
            "ri.actions.main.parameter.32d1ce35-0bc1-4935-ad18-ba4a45e8113f": {
                "type": "string",
                "string": limitations
            },
            # Provenance:
            "ri.actions.main.parameter.5577422c-02a4-454a-97d0-3fb76425ba8c": {
                "type": "string",
                "string": provenance
            },
            # Research project (1 of: [DomainTeam || ResearchProject] = required):
            "ri.actions.main.parameter.465404ad-c767-4d73-ab26-0d6e083eab8e": {
                "objectLocator": {
                    "objectTypeId": "research-project",
                    "primaryKey": {
                        "research_project_uid": {
                            "type": "string",
                            "string": "RP-4A9E27"
                        }
                    }
                }, "type": "objectLocator"
            },
            # Domain team (1 of: [DomainTeam || ResearchProject] = required):
            "ri.actions.main.parameter.4e790085-47ed-41ad-b12e-72439b645031": {
                "null": {},
                "type": "null"
            }  # domainTeam, optional only if research_id is submitted
        }
    }
    return cs_version_data



### 2/3. createNewDraftConceptSetVersion()
def post_cs_container(cs_name, token):
    """create a concept set container """
    url = f'https://unite.nih.gov/actions/api/actions'
    my_header = f'Authentication: Bearer {token}'
    container_data = get_cs_container_data(cs_name)
    response = requests.post( url, headers = my_header, data=container_data)
    r = response.json()
    return r


### 2/3. createNewDraftConceptSetVersion() (CreateNewConceptSet: concept_set_container_edited.csv)

# - 1 call per version
### data for creating a new draft version of the concept set - we will always be creating a version 1
### actionTypeRid: ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f
### parameters :
### concept_set_container object (object) ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8
### current max version number (integer) : ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13
### version to start with (object) :ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971
### update message (string) : ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e60324074661
### intention (string): ri.actions.main.parameter.2d5df665-6728-4f6e-83e5-8256551f8851
### limitations (string) : ri.actions.main.parameter.32d1ce35-0bc1-4935-ad18-ba4a45e8113f
### provenance (string) ri.actions.main.parameter.5577422c-02a4-454a-97d0-3fb76425ba8c
### intended research project (object): ri.actions.main.parameter.465404ad-c767-4d73-ab26-0d6e083eab8e
### domain team (object) : ri.actions.main.parameter.4e790085-47ed-41ad-b12e-72439b645031
# TODO: Amin said on 2022/01/28:
# hey foks, the create new version API call now has a new parameter that you will need to provide - the concept set version id of the version you're creating. You're responsible for its uniqueness, and you have a reserved range.
# Its id is  ri.actions.main.parameter.eac89354-a3bf-465e-a4be-bbf22a6e2c50
# and it's an integer in the following range: (1,000,000,000, 1,001,000,000).

cs_version_create_data = {
    "actionTypeRid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
    "parameters": {
            "ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8": {
                "type": "objectLocator",
                "objectLocator": 	{
                    "objectTypeId": "omop-concept-set-container",
                    "primaryKey": {
                        "concept_set_id": {
                            "type": "string",
                            "string": "<must match the concept name string specified in the container creation>"
                        }
                    }
                },
                "ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13": {
                    "type": "integer",
                    "integer": 1,
                },
                "ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971": {
                    "type": "objectLocator",
                    "objectLocator": 	{
                        "objectTypeId": "version_id",
                        "primaryKey": {
                            "version_id": {
                                "type": "integer",
                                "integer": 1
                            }
                        }
                    }
                },
                "ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e6032-4074661": {
                    "type": "string",
                    "string": "Initial [VSAC] version"
                },
                "ri.actions.main.parameter.2d5df665-6728-4f6e-83e5-8256551f8851" : {
                    "type": "string",
                    "string": "<intension string build from vsac source is set here>"
                },
                "ri.actions.main.parameter.32d1ce35-0bc1-4935-ad18-ba4a45e8113f": {
                    "type": "string",
                    "string": "<limitations text from vsac source is set here>"
                },
                "ri.actions.main.parameter.5577422c-02a4-454a-97d0-3fb76425ba8c": {
                    "type": "string",
                    "string": "<provenance built from the VSAC source is set here>"
                },
                "ri.actions.main.parameter.465404ad-c767-4d73-ab26-0d6e083eab8e": {
                    "type": "objectLocator",
                    "objectLocator": 	{
                        "objectTypeId": "research-project",
                        "primaryKey": {
                            "research_project_uid": {
                                "type": "string",
                                "string": "RP-4A9E27"
                            }
                        }
                    }
                }
            }
    }
}

### 3/3. add-code-system-codes-as-omop-version-expressions
# - bulk call for a single concept set; may contain many expressions in one call. can only do 1 concept set version per post request
# new api that will accept a codes and codeSystem instead of the concept_ids
# action item id: action type rid: ri.actions.main.action-type.e07f2503-c7c9-47b9-9418-225544b56b71
# use same id used to create the concept set version, the id is persisted in the csv files as the codeset_id in the
# concept_set_version_item_rv_edited.csv
### 3/3. createCodeSystemConceptVersionExpressionItems (addCodeAsVersionExpression: concept_set_version_item_rv_edited.csv)
# - bulk call for a single concept set; can contain many expressions in one call. can only do 1 concept set per call
# TODO: need more info: domain team (object) : ri.actions.main.parameter.4e790085-47ed-41ad-b12e-72439b645031
# TODO: How to know the ID of the concept set version created in the API:
#  - Amin said that in the API, we can accept the ID. they will validate that it is in the correct range. and if it is
#  valid, our POST request will succeed. and then we can re-use that version ID

def get_cs_version_expression_data(
    current_code_set_id: Union[str, int], cs_name: str, code_list: List[str], bExclude: bool, bDescendents: bool,
    bMapped: bool, annotation: str) -> Dict[str, Any]:
    cs_version_expression_data = {
        "actionTypeRid": "ri.actions.main.action-type.e07f2503-c7c9-47b9-9418-225544b56b71",
        "parameters": {
            # Version (object type): id used in version creation should be used
            "ri.actions.main.parameter.ad298972-0db3-4d85-9bbc-0c9ecd6ecf01": {
                "type": "objectLocator",
                "objectLocator": {
                    "objectTypeId": "version_id",
                    "primaryKey": {
                        "version_id": {
                            "type": "integer",
                            "integer": current_code_set_id
                        }
                    }
                }
            },
            # Exclude (boolean type): ri.actions.main.parameter.4a7ac14f-b292-4105-b7f5-5d0817b8cdc4
            "ri.actions.main.parameter.4a7ac14f-b292-4105-b7f5-5d0817b8cdc4": {
                "type": "boolean",
                "boolean": bExclude
            },

            # Include Descendents (boolean type): ri.actions.main.parameter.6cb950fd-894d-4176-9ad5-080373e26777
            "ri.actions.main.parameter.6cb950fd-894d-4176-9ad5-080373e26777": {
                "type": "boolean",
                "boolean": bDescendents
            },

            # Include Mapped (boolean type): ri.actions.main.parameter.1666c70c-0cb8-47c0-91e5-cb1d7e5bf316
            "ri.actions.main.parameter.1666c70c-0cb8-47c0-91e5-cb1d7e5bf316": {
                "type": "boolean",
                "boolean": bMapped
            },

            # Optional Annotation (string | null type): ri.actions.main.parameter.63e31a99-6b94-4580-b95a-a482ed64fed0
            "ri.actions.main.parameter.63e31a99-6b94-4580-b95a-a482ed64fed0": {
                "null": {},
                "type": "null"
            },

            # Codes (List of colon-delimited strings): ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33
            "ri.actions.main.parameter.c9a1b531-86ef-4f80-80a5-cc774d2e4c33": {
                "type": "stringList",
                "stringList": code_list
            }

        }
    }
    return cs_version_expression_data



