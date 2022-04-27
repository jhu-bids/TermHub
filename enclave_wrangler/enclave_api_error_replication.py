import requests
import json
import os
from dotenv import load_dotenv

load_dotenv("dih_n3c_service_acct_auth")
config = {
  'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN': os.getenv('PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN')
}

header = {
  "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
  'content-type': 'application/json'
}

# print(header)
api_url = 'https://unite.nih.gov/actions/api/actions'

data_dict = {
  "actionTypeRid": "ri.actions.main.action-type.ef6f89de-d5e3-450c-91ea-17132c8636ae",
  "parameters": {
    "ri.actions.main.parameter.1b5cd6e9-b220-4551-b97d-245b9fa86807": {
      "type": "string",
      "string": "[VSAC] Cerebrovascular Disease Stroke or TIA"
    },
    "ri.actions.main.parameter.28448734-2b6c-41e7-94aa-9f0d2ac1936f": {
      "type": "string",
      "string": "a39723f3-dc9c-48ce-90ff-06891c29114f"
    },
    "ri.actions.main.parameter.f04fd21f-4c97-4640-84e3-f7ecff9d1018": {
      "null": {},
      "type": "null"
    },
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
        "objectTypeId": "research-project",
        "primaryKey": {
          "research_project_uid": {
            "string": "RP-4A9E27",
            "type": "string"
          }
        }
      },
      "type": "objectLocator"
    }
  }
}

response = requests.post(api_url, data=json.dumps(data_dict), headers=header)

print(json.dumps(response.json(), indent=2))

