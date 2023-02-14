"""Extra utilities"""
import json
import logging
import sys
from typing import Dict, List, Union

import requests
from datetime import datetime, timezone, timedelta
from http.client import HTTPConnection

from requests import Response

from enclave_wrangler.config import config, TERMHUB_VERSION
from backend.utils import dump

EXTRA_PARAMS = {
    'create-new-draft-omop-concept-set-version': {
        "sourceApplication": "TermHub",
        "sourceApplicationVersion": TERMHUB_VERSION
    },
    'add-selected-concepts-as-omop-version-expressions': {
        "sourceApplication": "TermHub",
    },
}

SERVICE_TOKEN_KEY = 'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN'
PERSONAL_TOKEN_KEY = 'OTHER_TOKEN'
TOKEN_KEY = SERVICE_TOKEN_KEY


class EnclaveWranglerErr(RuntimeError):
    """Wrapper just to handle errors from this module"""


def get_headers(personal=False, content_type="application/json", for_curl=False):
    """Format headers for enclave calls

    TODO: fix all this -- we've been switching back and forth between service token and personal because some APIs are
      open to one, some to the other (and sometimes the service one has been expired. In the past we've switched by hard
      coding the api call header, but now we have to make api calls (temporarily, see
      https://cd2h.slack.com/archives/C034EG5ESU9/p1670337451241379?thread_ts=1667317248.546169&cid=C034EG5ESU9)
      using one and then the other."""
    # current_key = get_auth_token_key()
    # set_auth_token_key(personal)
    headers = {
        "authorization": f"Bearer {get_auth_token()}",
    }
    if content_type:    # call get_headers with content_type=None if you don't want that in the headers
        headers["Content-type"] = "application/json"

    # set_auth_token_key(current_key)
    if for_curl:
        headers["authorization"] = '$' + get_auth_token_key()
        headers = '\\\n'.join([f' -H "{k}: {v}"' for k, v in headers.items()])
    return headers

#     #"authorization": f"Bearer {config['PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN']}",

def set_auth_token_key(personal=False):
    global TOKEN_KEY
    TOKEN_KEY = PERSONAL_TOKEN_KEY if personal else SERVICE_TOKEN_KEY


def get_auth_token_key():
    return TOKEN_KEY


def get_auth_token():
    return config[TOKEN_KEY]


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
    response = requests.get(url, headers=get_headers(content_type=None))
    if response.status_code == 401:
        #Example:  '{"errorCode":"UNAUTHORIZED","errorName":"Default:Unauthorized","errorInstanceId":
        # "f035ae89-85c4-49a8-ab39-48942e8264bf","parameters":{"error":"EXPIRED"}}'
        return 0
    ttl = int(response.text)
    if ttl <= warning_threshold:
        days = timedelta(seconds=ttl).days
        print('Warning: Token expiring soon. You may want to renew. Days left: ' + str(days), file=sys.stderr)

    return ttl


def make_objects_request(path: str, verbose=False, url_only=False) -> Union[Response, str]:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    ontology_rid = config['ONTOLOGY_RID']
    path = path[1:] if path.startswith('/') else path
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    if url_only:
        return url
    if verbose:
        print(f'make_actions_request: {api_path}\n{url}')

    response = enclave_get(url, verbose=verbose)

    return response


def make_actions_request(api_name: str, data: Union[List, Dict] = None, validate_first=False, verbose=True) -> Response:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """

    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/actions/{api_name}/'
    url = f'https://{config["HOSTNAME"]}{api_path}'

    if api_name not in EXTRA_PARAMS:
        print(f"# should {api_name} have any EXTRA_PARAMS? it doesn't")
    else:
        data["parameters"].update(EXTRA_PARAMS[api_name])

    if validate_first:
        response: Response = enclave_post(url + 'validate', data, verbose=verbose)
        if not ('result' in response.json() and response.json()['result'] == 'VALID'):
            print(f'Failure: {api_name}\n', response, file=sys.stderr)
            return response

    response: Response = enclave_post(url + 'apply', data, verbose=verbose)

    return response


def enclave_post(url: str, data: Union[List, Dict], verbose=True) -> Response:
    """Post to the enclave and handle / report on some common issues"""
    if verbose:
        print_curl(url, data)

    headers = get_headers()
    try:
        response = requests.post(url, headers=headers, json=data)
        err = False
        if response.status_code >= 400:
            err = True
            print(f'Failure: {url}\n', response, file=sys.stderr)
        if any([x in response.text for x in ['errorCode', 'INVALID']]):
            err = True
            print('Error: ' + response.text, file=sys.stderr)
        # response.raise_for_status()
        if err:
            raise EnclaveWranglerErr(response.status_code, ': ', response.text)

        return response
    except Exception as err:
        ttl = check_token_ttl(get_auth_token())
        if ttl == 0:
            raise RuntimeError(f'Error: Token expired: ' + get_auth_token_key())
        raise err


def enclave_get(url: str, verbose: bool = True, args: Dict = {}) -> Response:
    """Get from the enclave and print curl"""
    if verbose:
        print_curl(url, args=args)
    headers = get_headers()
    response = requests.get(url, headers=headers, **args)
    return response


def relevant_trace():
    """Get the relevant part of the stack trace"""
    import traceback
    import re
    from enclave_wrangler.config import PROJECT_ROOT
    stack = traceback.format_stack()
    matches = [re.search(f'.*{PROJECT_ROOT}[^"]*", line \d+', c) for c in stack]
    trace = [m[0] for m in matches if m]
    trace = [t for t in trace if not re.search('/venv/', t)]
    return '\n'.join(trace)


def print_curl(url: str, data: Union[List, Dict]=None, args: Dict = {}, trace:bool=False):
    """Print curl command for debugging"""
    curl = f"""\ncurl {get_headers(for_curl=True)} \\
            {url}"""
    if data:
        curl += f" \\\n--data '{json.dumps(data)}' | jq\n"
    if args:
        curl += f" additional args:{dump(args)}\n\n"
    if trace:
        curl += relevant_trace()
    print(curl)  # printing to debugger during test doesn't work; have to do it manually


# def old_get(api_name: str, validate=False)-> Response:
#     """For GET request"""
#     return make_actions_request(api_name, validate=validate)
#
#
# def old_post(api_name: str, data: Dict, validate_first=VALIDATE_FIRST)-> Response:
#     """For POST request"""
#     if validate_first:
#         response: Response = make_actions_request(api_name, data, validate=True)
#         if not ('result' in response.json() and response.json()['result'] == 'VALID'):
#             print(f'Failure: {api_name}\n', response, file=sys.stderr)
#             return response
#     return make_actions_request(api_name, data, validate=False)
