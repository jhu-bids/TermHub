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
from typing import Dict

import requests


## 1/3. Create new concept set container
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
def get_cs_container_data( cs_name: str ) -> Dict:
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
def get_cs_version_data ( cs_name, cs_id, intention, limitations, update_msg, provenance   ):

    cs_version_data = {
        # create new draft concept set version
        "actionTypeRid": "ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f",
        "parameters": {
            "ri.actions.main.parameter.eac89354-a3bf-465e-a4be-bbf22a6e2c50": {
                "type": "integer",
                "integer ": 1000000000 ## TODO use cs_id here
            },  # concept_id, must be within the range given by Palantir
            "ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8": {
                "type": "objectLocator",
                "objectLocator": {
                    "objectTypeId": "omop-concept-set-container",
                    "primaryKey": {
                        "concept_set_id": {
                            "type": "string",
                            # must match the concept name string specified in the container creation
                            "string": "stephanie cs example" ## TODO use cs_name here
                        }}}
                },  # cs_container_name
            "ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13": {
                "null": {},
                "type": "null"
            },  # deprecated, but required until it is dropped, current max version
            "ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971": {
                "null": {},
                "type": "null"
            },  # legacy version, but required for now, version to start with which is 1
            "ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e6032<4074661": {
                "type": "string",
                "string": update_msg
            },  # update_message
            "ri.actions.main.parameter.2d5df665-6728-4f6e-83e5-8256551f8851": {
                "type": "string",
                "string": intention
            },  # intention string generated from vsac source
            "ri.actions.main.parameter.32d1ce35-0bc1-4935-ad18-ba4a45e8113f": {
                "type": "string",
                "string": limitations
            },  # limitations text generated from vsac
            "ri.actions.main.parameter.5577422c-02a4-454a-97d0-3fb76425ba8c": {
                "type": "string",
                "string": provenance
            },  # provenance generated from vsac
            "ri.actions.main.parameter.465404ad-c767-4d73-ab26-0d6e083eab8e": {
                "objectLocator": {
                    "objectTypeId": "research-project", "primaryKey": {
                        "research_project_uid": {
                            "type": "string",
                            "string": "RP-4A9E27"
                        }
                    }
                }, "type": "objectLocator"
            }  # research_project
        }  # eof parameters
    }
    return cs_version_data

## PLEASE READ THIS NOTE!!!
## IMPORTANT: the authentication bearer token value cannot be uploaded to gitHub
## if that happens the token will become invalidated
## THIS TOKEN IS FOR OUR JHU TEAM USE ONLY!!!
## following code
def post_cs_container( cs_name ):
    """create a concept set container """

    url = f'https://unite.nih.gov/actions/api/actions'
    my_header = f'Authentication: Bearer 1351351351t3135dfadgaddt'
    container_data = get_cs_container_data (cs_name)
    response = requests.post( url, headers = my_header, data=container_data)

    r = response.json()
    return r


### 2/3. createNewDraftConceptSetVersion()
# - 1 call per version
### data for creating a new draft version of the concept set - we will always be creating a version 1
### actionTypeRid: ri.actions.main.action-type.fb260d04-b50e-4e29-9d39-6cce126fda7f
### parameters :
### concept_set_container object (object) ri.actions.main.parameter.51e12235-c217-47e2-a347-240d379434e8
### current max version number (integer) : ri.actions.main.parameter.c58b7fa6-e6b4-49ad-8535-433507fe3d13
### version to start with (object) :ri.actions.main.parameter.c3e857d9-a9d8-423c-9dec-610e4e90f971
### update message (string) : ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e6032<4074661
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
        "params": {
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
                "ri.actions.main.parameter.ae8b8a16-c690-42fa-b828-e6032<4074661": {
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
}

    ### 3/3. createCodeSystemConceptVersionExpressionItems
    # - bulk call for a single concept set; can contain many expressions in one call. can only do 1 concept set per call
    # TODO: Plantir to expose new api that will accept a codes and codeSystem instead of the concept_ids
    # TODO: need more info: domain team (object) : ri.actions.main.parameter.4e790085-47ed-41ad-b12e-72439b645031
    # TODO: How to know the ID of the concept set version created in the API:
    #  - Amin said that in the API, we can accept the ID. they will validate that it is in the correct range. and if it is
    #  valid, our POST request will succeed. and then we can re-use that version ID

    # 4. A mapping table, I believe, that Amin is creating/exposing for us, for converting to standard codes



