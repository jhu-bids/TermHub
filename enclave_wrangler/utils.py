"""Extra utilities"""
import logging
import sys

import requests
from datetime import datetime, timezone, timedelta
from http.client import HTTPConnection


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
