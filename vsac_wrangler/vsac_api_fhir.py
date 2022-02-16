"""Get value sets from VSAC

Docs:
- https://documentation.uts.nlm.nih.gov/rest/authentication.html
- https://www.nlm.nih.gov/vsac/support/usingvsac/vsacfhirapi.html
"""
from typing import Dict, List, OrderedDict
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth
import urllib3.util
# import xmltodict as xd
from vsac_wrangler.config import config

API_KEY = config['vsac_api_key']

def get_value_set(oid: str) -> Dict:
    """Get a value set"""
    # url = f'https://cts.nlm.nih.gov/fhir/ValueSet/{oid}&ticket={service_ticket}'
    url = f'https://cts.nlm.nih.gov/fhir/ValueSet/{oid}'

    # from https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module/16511493#16511493
    try:
        r = requests.get(url, auth=HTTPBasicAuth('', API_KEY))
        r.raise_for_status()
        return r.json()
    #except requests.exceptions.HTTPError as err:
    except Exception as err:
        raise SystemExit(err)

# TODO: Figure out if / how I want to cache this
# 11 seconds to fetch all 62 oids
def get_value_sets(oids: List[str]) -> OrderedDict:
    """
    version with old VSAC API could grab multiple OIDs at the same time. not sure yet with FHIR

    oids_str = ','.join(oids)
    url = f'https://vsac.nlm.nih.gov/vsac/svs/RetrieveMultipleValueSets?id={oids_str}&ticket={service_ticket}'
    response = requests.get(
        url=url,
        data={'apikey': API_KEY})
    xml_str = response.text
    d: OrderedDict = xd.parse(xml_str)
    """
    vsets = {}

    for oid in oids:
        vset = get_value_set(oid)
        vsets[oid] = vset

    return vsets
