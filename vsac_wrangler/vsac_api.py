"""Get value sets from VSAC

Docs:
- https://documentation.uts.nlm.nih.gov/rest/authentication.html
- https://www.nlm.nih.gov/vsac/support/usingvsac/vsacfhirapi.html
"""
from typing import Dict, List, OrderedDict

from bs4 import BeautifulSoup
import requests
import urllib3.util
import xmltodict as xd

from vsac_wrangler.config import config


API_KEY = config['vsac_api_key']


# TODO: This only needs to be done once a day
def get_ticket_granting_ticket() -> str:
    """Get TGT (Ticket-granting ticket)"""
    # 'curl -X POST https://utslogin.nlm.nih.gov/cas/v1/api-key -H 'content-type: application/x-www-form-urlencoded'
    #   -d apikey={your_api_key_here}'
    response = requests.post(
        url='https://utslogin.nlm.nih.gov/cas/v1/api-key',
        data={'apikey': API_KEY})
    # Siggie: Sometimes the URL returned works as TGT; and sometimes the TGT string itself will serve as the TGT.
    soup = BeautifulSoup(response.text, 'html.parser')
    tgt_url = soup.find('form').attrs['action']
    ticket_granting_ticket = urllib3.util.parse_url(tgt_url).path.split('/')[-1]

    return ticket_granting_ticket


def get_service_ticket(tgt) -> str:
    """Get single-use service ticket

    Params:
        tgt (str): Ticket granting ticket
    """
    # curl -X POST https://utslogin.nzlm.nih.gov/cas/v1/tickets/{your_TGT_here} -H 'content-type:
    #   application/x-www-form-urlencoded' -d service=http%3A%2F%2Fumlsks.nlm.nih.gov
    # - Any of the 3 urls below will work
    response2 = requests.post(
        url='https://utslogin.nlm.nih.gov/cas/v1/tickets/{}'.format(tgt),
        # url='https://utslogin.nlm.nih.gov/cas/v1/api-key/{}'.format(ticket_granting_ticket),
        # url='https://vsac.nlm.nih.gov/vsac/ws/Ticket/{}'.format(ticket_granting_ticket),
        data={'service': 'http://umlsks.nlm.nih.gov'},
        headers={'Content-type': 'application/x-www-form-urlencoded'})
    service_ticket = response2.text

    return service_ticket


def get_value_set(oid: str, tgt: str) -> Dict:
    """Get a value set"""
    service_ticket = get_service_ticket(tgt)
    # url = f'https://cts.nlm.nih.gov/fhir/ValueSet/{oid}&ticket={service_ticket}'
    url = f'https://vsac.nlm.nih.gov/vsac/svs/RetrieveValueSet?id={oid}&ticket={service_ticket}'
    response = requests.get(
        url=url,
        data={'apikey': API_KEY})
    xml_str = response.text
    d: OrderedDict = xd.parse(xml_str)

    return d


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# 11 seconds to fetch 62 oids
def get_value_sets(oids: List[str], tgt: str, n_oids_per_req=200) -> List[OrderedDict]:
    """Get multiple value sets.

    :param n_oids_per_req: In our experience, VSAC returns error 400 when a certain number of OIDs
    gets passed; somewhere between 220-250. Therefore, arbitrarily deciding to chunk requests at 200 OIDs each."""
    d_list: List[OrderedDict] = []
    for chunk in chunks(oids, n_oids_per_req):
        oids_str = ','.join(chunk)
        service_ticket = get_service_ticket(tgt)
        url = f'https://vsac.nlm.nih.gov/vsac/svs/RetrieveMultipleValueSets?id={oids_str}&ticket={service_ticket}'
        response = requests.get(
            url=url,
            data={'apikey': API_KEY})
        xml_str = response.text
        d: OrderedDict = xd.parse(xml_str)
        d_list.append(d)

    final_d: OrderedDict = d_list[0]
    key1 = 'ns0:RetrieveMultipleValueSetsResponse'
    key2 = 'ns0:DescribedValueSet'

    value_sets: List[OrderedDict]
    if len(d_list) > 1:
        for d in d_list[1:]:
            final_d[key1][key2] += d[key1][key2]
        value_sets = final_d[key1][key2]
    elif type(final_d[key1][key2]) == list:
        value_sets = final_d[key1][key2]
    elif str(type(final_d[key1][key2])) == '<class \'collections.OrderedDict\'>':
        value_sets = [final_d[key1][key2]]

    return value_sets
