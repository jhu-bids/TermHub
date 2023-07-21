"""Extra utilities"""
import json
import logging
import os
import sys
from typing import Dict, List, Union
from random import randint
from time import sleep, time
import urllib.parse

import pandas as pd
import requests
from datetime import datetime, timezone, timedelta
from http.client import HTTPConnection

from requests import Response

from enclave_wrangler.config import OUTDIR_OBJECTS, config, TERMHUB_VERSION, CSET_VERSION_MIN_ID
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
JSON_TYPE = Union[Dict, List]
SERVICE_TOKEN_KEY = 'PALANTIR_ENCLAVE_AUTHENTICATION_BEARER_TOKEN'
PERSONAL_TOKEN_KEY = 'OTHER_TOKEN'
TOKEN_KEY = SERVICE_TOKEN_KEY


class EnclaveWranglerErr(RuntimeError):
    """Wrapper just to handle errors from this module"""

class EnclavePaginationLimitErr(RuntimeError):
    """Wrapper just to handle errors from this module"""
    msg = "Enclave errored on paginated request on page {}, with status code {}, with {} items in results."

class ActionValidateError(RuntimeError):
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
    """Sets the key to be looked up for the auth token for the N3C Palantir Foundry data enclave."""
    global TOKEN_KEY
    TOKEN_KEY = PERSONAL_TOKEN_KEY if personal else SERVICE_TOKEN_KEY


def get_auth_token_key():
    """Returns the key to be looked up for the auth token for the N3C Palantir Foundry data enclave."""
    return TOKEN_KEY


def get_auth_token():
    """Returns the auth token for the N3C Palantir Foundry data enclave."""
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
    """Set debug requests to off"""
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


def check_token_ttl(token: str, warning_threshold=60 * 60 * 24 * 14, warn_anyway=False):
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
    if ttl <= warning_threshold or warn_anyway:
        days = timedelta(seconds=ttl).days
        print('Warning: Token expiring soon. You may want to renew. Days left: ' + str(days) +
              ': ' + str((datetime.now() + timedelta(days=149)).date()), file=sys.stderr)

    return ttl


def response_failed(response: Response) -> bool:
    """Return True if response failed, else False"""
    return response.status_code >= 400  # check anything else ever?


def handle_response_error(
    response: Response, error_dir: Union[str, None] = None, fail: bool = False, calling_func: str = 'response error'
):
    """This code was taken out of make_objects_request() (formerly get_objects_by_type()). Trying to use it
    for all Response errors now. Not sure if it's entirely appropriate."""
    failed = response_failed(response)
    if failed:
        print(f'Error: {calling_func}: {str(response.status_code)} {response.reason}', file=sys.stderr)
        error_report: Dict = {'request': response.url, 'response': response.json()}
        print(error_report, file=sys.stderr)
        curl_str = f'curl -H "Content-type: application/json" ' \
                   f'-H "Authorization: Bearer ${get_auth_token_key()}" {response.url}'
        print(curl_str, file=sys.stderr)
        if error_dir:
            with open(os.path.join(error_dir, f'error {response.status_code}.json'), 'w') as file:
                json.dump(error_report, file)
            with open(os.path.join(error_dir, f'error {response.status_code} - curl.sh'), 'w') as file:
                file.write(curl_str)

        # TODO: what else could be in response? (Joe: potentially, to this function, we could pass a custom err message
        #  to display if it if fails
        raise EnclaveWranglerErr({
            "status_code": response.status_code,
            "text": response.text,
            # ... ?
        })


def enclave_get(url: str, verbose: bool = True, args: Dict = {}, error_dir: str = None) -> Response:
    """Get from the enclave and print curl"""
    if verbose:
        print_curl(url, args=args)
    headers = get_headers()
    response = requests.get(url, headers=headers, **args)
    handle_response_error(response, error_dir)
    return response


def handle_paginated_request(
    first_page_url: str, verbose=False, error_dir: str = None
) -> (List[Dict], Response):
    """Handles a request that has a nextPageToken, automatically fetching all pages and combining the data"""
    url = first_page_url
    results: List[Dict] = []
    i = 0
    while True:
        i += 1
        try:
            response = enclave_get(url, verbose=verbose, error_dir=error_dir)
        except EnclaveWranglerErr as err:
            if results:
                err.args[0]['results_prior_to_error'] = results
            status_code = err.args[0]['status_code']
            # TODO: better to check for 'errorName': 'ObjectsExceededLimit' in the response
            if status_code == 400 and len(results) >= 10000:
                raise EnclavePaginationLimitErr(
                    EnclavePaginationLimitErr.msg.format(str(i), status_code, len(results)), err.args[0])
            else:
                raise err

        response_json = response.json()
        results += response_json['data']
        if 'nextPageToken' not in response_json or not response_json['nextPageToken']:
            break
        url = first_page_url + '?pageToken=' + response_json["nextPageToken"]
    return results


def get_objects_df(object_type, outdir: str = None, save_csv=True, save_json=True):
    """Get objects as dataframe"""
    # Get objects
    objects: List[Dict] = make_objects_request(object_type, return_type='data', outdir=outdir, handle_paginated=True)

    # Parse
    # Get rid of nested 'properties' key, and add 'rid' in with the other fields
    df = pd.DataFrame()
    if objects:
        results = [{**x['properties'], **{'rid': x['rid']}} for x in objects]
        df = pd.DataFrame(results).fillna('')

    # Save
    if outdir:
        outdir = outdir if outdir else os.path.join(OUTDIR_OBJECTS, object_type)
        outpath = os.path.join(outdir, 'latest.csv')
        if not os.path.exists(outdir) and (save_json or save_csv):
            os.mkdir(outdir)
        # - csv
        if save_csv:
            df.to_csv(outpath, index=False)
        # - json
        if save_json:
            with open(outpath.replace('.csv', '.json'), 'w') as f:
                json.dump(objects, f)
    return df


def get_url_from_api_path(path):
    """Construct path for enclave API url"""
    ontology_rid = config['ONTOLOGY_RID']
    path = path[1:] if path.startswith('/') else path
    api_path = f'/api/v1/ontologies/{ontology_rid}/{path}'
    url = f'https://{config["HOSTNAME"]}{api_path}'
    return url


def fetch_objects_since_datetime(object_type: str, since: Union[datetime, str], verbose=False) -> List[Dict]:
    """Fetch objects since a specific datetime

    :param: since: Must be in ISO 8601 format with timezone offset: YYYY-MM-DDTHH:MM:SS.SSSSSS+HH:MM"""
    since = str(since)
    try:
        return make_objects_request(
            object_type, query_params={'properties.createdAt.gt': since}, verbose=verbose, return_type='data',
            handle_paginated=True)
    except EnclaveWranglerErr as e:
        raise ValueError(f'Invalid timestamp: {since}. Make sure it is in ISO 8601 format with timezone offset: '
                         f'YYYY-MM-DDTHH:MM:SS.SSSSSS+HH:MM.') if 'timestamp' in str(e).lower() else e


# TODO: Should we automatically handle_paginated?
#  - Siggie said that the issue is that when we do that, we don't return a response. Maybe like 3 instances of calls
#  that need a response object instead of JSON data. But for those why don't explicitly pass return_type=Response?
# todo's from b4 refactor combining make_objects_request() and get_objects_by_type() 2023/03/15
#   1. Need to find the right object_type, then write a wrapper func around this to get concept sets
#     - To Try: CodeSystemConceptSetVersionExpressionItem, OMOPConcept, OMOPConceptSet, OMOPConceptSetContainer,
#     OmopConceptSetVersionItem
#   2. connect to `manage` table and get since last datetime. for now, use below as example
# noinspection PyUnboundLocalVariable
# TODO: make pagination automatic, but need to make sure that every call to make_objects_request is requesting
#   return type data (and remove that parameter, or make data the default at least)
def make_objects_request(
    path: str, verbose=False, url_only=False, return_type: str = ['Response', 'json', 'data'][0],
    handle_paginated=False, expect_single_item=False, retry_if_empty=False, retry_times=15, retry_pause=1,
    outdir: str = None, query_params: Dict = None, fail_on_error=True, **request_args
        # why isn't fail_on_error implemented?
) -> Union[Response, JSON_TYPE, str]:
    """Fetch objects from enclave

    :param return_type： should be Response, json, or data

    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/object-basics/
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """
    try:
        # Validation
        if handle_paginated and return_type != 'data':
            raise EnclaveWranglerErr("if handling paginated, data is the only allowable return_type")

        # Conditional params
        retry_times, retry_pause = (1, 0) if not retry_if_empty else (retry_times, retry_pause)

        # Construct URL
        url: str = get_url_from_api_path(f'objects/{path}')
        url = url.replace('/objects/objects', '/objects') # in case path already has 'objects' at the beginning
        if query_params:
            # was: url = url + '?' + '&'.join(query_params) if query_params else url
            # urllib.parse.quote turns spaces into + instead of %20, i got this
            #   fix from https://stackoverflow.com/a/44829021
            url = url + '?' + urllib.parse.urlencode(
                query_params, quote_via=urllib.parse.quote)

        if url_only:
            return url

        # Fetch data
        for i in range(retry_times):
            if retry_if_empty:
                print(f'make_objects_request, attempt #{i}')
            if handle_paginated:
                data: List[Dict] = handle_paginated_request(url, verbose=verbose, error_dir=outdir)
                if data:
                    return data
            else:
                response: Response = enclave_get(url, verbose=verbose, error_dir=outdir, **request_args)
                response_json: JSON_TYPE = response.json()
                # single items don't have 'data', just 'properties' at the top
                data: List[Dict] = response_json['properties'] if expect_single_item else response_json['data']
                if data:
                    break
            sleep(retry_pause)
    except Exception as err:
        if fail_on_error:
            raise err
        else:
            print(err)
            return

    # Return
    if return_type == 'Response':
        return response
    if return_type == 'json':        # do error checking/handling?
        return response_json
    if return_type == 'data':
        return data


def make_actions_request(
    api_name: str, data: Union[List, Dict] = None, validate_first=False, raise_validate_error=False, verbose=True
) -> Response:
    """Passthrough for HTTP request
    If `data`, knows to do a POST. Otherwise does a GET.
    Enclave docs:
      https://www.palantir.com/docs/foundry/api/ontology-resources/objects/list-objects/
      https://www.palantir.com/docs/foundry/api/ontology-resources/object-types/list-object-types/
    """

    if not "parameters" in data:
        raise KeyError("expecting data to be wrapped in 'parameters' property")

    ontology_rid = config['ONTOLOGY_RID']
    api_path = f'/api/v1/ontologies/{ontology_rid}/actions/{api_name}/'
    url = f'https://{config["HOSTNAME"]}{api_path}'

    if api_name not in EXTRA_PARAMS:
        print(f"# should {api_name} have any EXTRA_PARAMS? it doesn't")
    else:
        data["parameters"].update(EXTRA_PARAMS[api_name])

    if validate_first:
        response: Response = enclave_post(
            url + 'validate', data, raise_validate_error=raise_validate_error, verbose=verbose)
        if not ('result' in response.json() and response.json()['result'] == 'VALID'):
            print(f'Failure: {api_name}\n', response, file=sys.stderr)
            return response

    response: Response = enclave_post(url + 'apply', data, verbose=verbose)

    return response


def process_validate_errors(response: Response, errType: Exception=None, print_error=False):
    """Process validate errors"""
    if response.status_code >= 400:
        if errType:
            raise errType(response.json())
        return response.json()
    validate_errors = response.json()
    if not validate_errors['result'] == 'INVALID':
        raise EnclaveWranglerErr("that's not what I expected")

    out_errors = {}
    for x in validate_errors['submissionCriteria']:
        out_errors['submissionCriteria'] = out_errors['submissionCriteria'] or []
        out_errors['submissionCriteria'].append(x['configuredFailureMessage'])
    invalid_params = {}
    for k, v in validate_errors['parameters'].items():
        if v['result'] == 'INVALID':
            invalid_params[k] = v
    if invalid_params:
        out_errors['invalid_params'] = invalid_params
        # out_errors.append('invalid params:')
        for k, v in invalid_params.items():
            # out_errors.append(k)
            if v['evaluatedConstraints']:
                pass
                # out_errors.append(v['evaluatedConstraints'])
    if print_error:
        print(dump(out_errors), file=sys.stderr)
    if errType:
        raise errType(out_errors)
    return out_errors


def enclave_post(url: str, data: Union[List, Dict], raise_validate_error: bool=False, verbose=True) -> Response:
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
            if raise_validate_error:
                process_validate_errors(response, errType=ActionValidateError)
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


def get_random_codeset_id() -> int:
    """Generage random Codeset ID"""
    # todo: this is temporary until I handle registry persistence
    arbitrary_range = 100000
    codeset_id = randint(CSET_VERSION_MIN_ID, CSET_VERSION_MIN_ID + arbitrary_range)
    return codeset_id


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


def was_file_modified_within_threshold(path: str, threshold_hours: int) -> bool:
    """Check if a file was modified within a certain threshold"""
    diff_hours = (time() - os.path.getmtime(path)) / (60 * 60)
    return diff_hours <= threshold_hours


if __name__ == '__main__':
    cset_name = 'Hope Termhub Test'
    codeset_id = 27371375

    x = make_actions_request('edit-concept-set-version-intention',
                         data={ 'parameters': {
                             'omop-concept-set': codeset_id,
                             'intention': f'testing on july 19'
                         }}, validate_first=True)
    print(x)

    x = make_actions_request('archive-concept-set',
                             data={'parameters': { 'concept-set': cset_name, }}, validate_first=True)
    print(x)

