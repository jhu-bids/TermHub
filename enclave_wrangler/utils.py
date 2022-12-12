"""Extra utilities"""
import json
import logging
import sys
from typing import Dict, List, Union

import requests
from datetime import datetime, timezone, timedelta
from http.client import HTTPConnection

from requests import Response

from enclave_wrangler.config import VALIDATE_FIRST, config

# TODO: fix all this -- we've been switching back and forth between service token and personal
#       because some APIs are open to one, some to the other (and sometimes the service one has
#       been expired. In the past we've switched by hard coding the api call header, but now
#       we have to make api calls (temporarily, see https://cd2h.slack.com/archives/C034EG5ESU9/p1670337451241379?thread_ts=1667317248.546169&cid=C034EG5ESU9)
#       using one and then the other
#
# "authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",
# "authorization": f"Bearer {config['OTHER_TOKEN']}",
SERVICE_TOKEN_KEY = 'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN'
PERSONAL_TOKEN_KEY = 'OTHER_TOKEN'
TOKEN_KEY = SERVICE_TOKEN_KEY


def log_debug_info():
    """Logs additional info when making HTTP requests"""
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib2 as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def debug_requests_off():
    # ''' Switches off logging of the requests module, might be some side-effects '''
    HTTPConnection.debuglevel = 0

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    root_logger.handlers = []
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.WARNING)
    requests_log.propagate = False


def _datetime_palantir_format() -> str:
    """Returns datetime str in format used by palantir data enclave
    e.g. 2021-03-03T13:24:48.000Z (milliseconds allowed, but not common in observed table)"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + 'Z'


def check_token_ttl(token: str, warning_threshold=60 * 60 * 24 * 14):
    """Given an auth token, call the API and check TTL (Time To Live).

    :param token: An auth token for the N3C Palantir Foundry data enclave.
    :param warning_threshold: The amount of time by which, if ttl is less than this, will print a warning.
      Default: 60 * 60 * 24 * 14 (two weeks).

    Example:
        curl -XGET https://unite.nih.gov/multipass/api/token/ttl \
        -H "Authorization: Bearer $PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN"
    """
    #
    url = 'https://unite.nih.gov/multipass/api/token/ttl'
    response = requests.get(url, headers={'Authorization': f"Bearer {token}"})
    if response.status_code == 401:
        #Example:  '{"errorCode":"UNAUTHORIZED","errorName":"Default:Unauthorized","errorInstanceId":
        # "f035ae89-85c4-49a8-ab39-48942e8264bf","parameters":{"error":"EXPIRED"}}'
        return 0
    ttl = int(response.text)
    if ttl <= warning_threshold:
        days = timedelta(seconds=ttl).days
        print('Warning: Token expiring soon. You may want to renew. Days left: ' + str(days), file=sys.stderr)

    return ttl


def make_request(api_name: str, data: Union[List, Dict] = None, validate=False, verbose=True) -> Response:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    # temporarily!!!
    headers = {
        # todo: When/if @Amin et al allow enclave service token to write to the new API, change this back from.
        "authorization": f"Bearer {get_auth_token()}",
        "Content-type": "application/json",

    }
    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/actions/{api_name}/'
    api_path += 'validate' if validate else 'apply'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    if verbose:
        # print(f'make_request: {api_path}\n{url}')
        print(f"""\ncurl  -H "Content-type: application/json" \\
            -H "Authorization: Bearer ${get_auth_token_key()}" \\
            {url} \\
            --data '{json.dumps(data)}'
            """)

    # try:
    if data:
        response = requests.post(url, headers=headers, json=data)
    else:
        response = requests.get(url, headers=headers)
    try:
        if 'errorCode' in response.text:
            print('Error: ' + response.text)
        response.raise_for_status()
    except Exception as err:
        ttl = check_token_ttl(get_auth_token())
        if ttl == 0:
            raise RuntimeError(f'Error: Token expired: ' + get_auth_token_key())
        raise err

    return response


def make_read_request(path: str, verbose=False) -> Response:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    headers = {
        "authorization": f"Bearer {get_auth_token()}",
        "Content-type": "application/json",

    }
    ontology_rid = config['ONTOLOGY_RID']
    path = path[1:] if path.startswith('/') else path
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    if verbose:
        print(f'make_request: {api_path}\n{url}')

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response


def get(api_name: str, validate=False)-> Response:
    """For GET request"""
    return make_request(api_name, validate=validate)


def post(api_name: str, data: Dict, validate_first=VALIDATE_FIRST)-> Response:
    """For POST request"""
    if validate_first:
        response: Response = make_request(api_name, data, validate=True)
        if not ('result' in response.json() and response.json()['result'] == 'VALID'):
            print(f'Failure: {api_name}\n', response, file=sys.stderr)
            return response
    return make_request(api_name, data, validate=False)


def set_auth_token_key(personal=False):
    global TOKEN_KEY
    TOKEN_KEY = PERSONAL_TOKEN_KEY if personal else SERVICE_TOKEN_KEY


def get_auth_token_key():
    return TOKEN_KEY


def get_auth_token():
    return config[TOKEN_KEY]
