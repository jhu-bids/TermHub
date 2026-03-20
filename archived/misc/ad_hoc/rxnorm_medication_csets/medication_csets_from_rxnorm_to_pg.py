import io, csv, json, os, time
from typing import Dict, List, Union
import requests
from requests import Response
# from mezmorize import Cache
import pandas as pd

from backend.db.utils import get_db_connection, sql_query_single_col, sql_in, insert_from_dict, sql_query
from backend.utils import pdump
from enclave_wrangler.dataset_upload import upload_new_container_with_concepts
from enclave_wrangler.objects_api import cset_container_and_version_enclave_to_db

BASE_RXNORM_URL = "https://rxnav.nlm.nih.gov"

CON = get_db_connection()


# config = {
#   'DEBUG': True,
#   'CACHE_TYPE': 'filesystem',
#   'CACHE_DIR': 'cached_calls',
# }
# cache = Cache(**config)


def get_med_csets():
  """
  with Medication Concept Set for N3C csv
  exported from https://docs.google.com/spreadsheets/d/15ov0i7zeWX9sStROPKIYv2x6F7ok1v1g_C-yp3eJKOc
    1. get related rxcuis for rxcui listed
    2. translate into concept_ids
    3. save (how?) as concept set for comparison in TermHub
    4. launch termhub comparison page with that cset as well as those listed
       in the google sheet column compare_n3c_codeset_ids
  get codesets to compare

  allrelated api call returns object like:
    {
    "allRelatedGroup": {
      "rxcui": "",
      "conceptGroup": [
        {
          "tty": "BN",
          "conceptProperties": [
            {
              "rxcui": "1009389",
              "name": "Tresaderm",
              "synonym": "",
              "tty": "BN",
              "language": "ENG",
              "suppress": "N",
              "umlscui": ""
            },
            {
              "rxcui": "1049383",
              ...
  """
  cr = csv.DictReader(io.open('./med-csets.csv'))
  # print(json.dumps(list(cr), indent=2))
  all_rows = []
  for cset in cr:
    rxcui = cset['RXCUI']
    cset_name = cset['CSET NAME']
    if not rxcui.isdigit():
      print(f"invalid rxcui [{rxcui}] for {cset_name}")
      continue
    print(f"getting related for {rxcui}:{cset['CSET NAME']}")
    data = rxnorm_get(rxcui)
    terms = [{k: term[k] for k in ('rxcui', 'tty', 'name')} for term in data]

    # for Tanner
    for term in terms:
      q = f"""
        SELECT  
                '{cset_name}' AS cset_name,
                '{rxcui}' AS cset_rxcui,
                '{term['rxcui']}' AS rxcui, 
                '{term['tty']}' AS tty, 
                '{term['name']}' AS rxnorm_name, 
                concept_id,
                concept_name,
                concept_class_id
        FROM concept
        WHERE vocabulary_id = 'RxNorm' 
          AND concept_code = '{term['rxcui']}'
      """
      rows = sql_query(CON, q)
      all_rows.extend(rows)

  df = pd.DataFrame(all_rows)
  df.to_csv('./rxnorm_csets_for_tanner.csv')






  # rxcuis = {t['rxcui'] for t in terms}
  #   cids = rxcuis_to_concept_ids(rxcuis)
    # create_rxnorm_cset: Puts it directly into Postgres
    # create_rxnorm_cset(rxcui, f'RxNorm: {cset_name}', ','.join([str(c) for c in cids]))
    # upload_and_sync_rxnorm_cset(rxcui, f'RxNorm: {cset_name}', cids)

    # compare_cids = cset['compare_n3c_codeset_ids']


# @cache.memoize(timeout=60*60*24*365)
def rxnorm_get(rxcui):
  call = f"{BASE_RXNORM_URL}/REST/rxcui/{rxcui}/allrelated.json" # ?tty=SCDF"  # tty=MIN+DFG+DF" # +SBD
  print(f"calling {call}")
  data = requests.get(call)
  data = data.json()

  # unwrap top two levels of json structure
  data = data['allRelatedGroup']['conceptGroup']
  # that gives a list grouped by tty, each tty has list of conceptProperties
  # which are the terms we want to get
  data = [d['conceptProperties'] for d in data if 'conceptProperties' in d]
  # flatten the tty-grouped lists into a single list
  data = [item for sublist in data for item in sublist]
  print(f"got {len(data)} rxcuis. sleeping for 3 to not error on")
  # time.sleep(3)
  return data


  # CREATE TABLE rxnorm_med_cset(
  #   rxcui text,
  #   cset_name text,
  #   concept_ids text)
def create_rxnorm_cset(rxcui, cset_name, concept_ids):
  insert_from_dict(CON, 'rxnorm_med_cset', {
    'rxcui': rxcui,
    'cset_name': cset_name,
    'concept_ids': concept_ids
  })


def rxcuis_to_concept_ids(rxcuis):
  q = f"""
    select concept_id
    from concept
    where vocabulary_id = 'RxNorm' 
      and concept_code {sql_in(rxcuis, quote_items=True)}
  """
  cids = sql_query_single_col(CON, q)
  return cids


def upload_and_sync_rxnorm_cset(rxcui: int, cset_name: str, concept_ids: List[int]):
    """Upload RxNorm concept sets to the enclave and then sync back to our database.
    todo: later?: check if already exists in termhub before uploading. where? code_sets.concept_set_version_title
    """
    # TODO: Upload any new concept sets to the enclave
    #  (this will fail if the concept set name already exists)
    #  - fetch this information from table
    #  - then do the whole thing to upload to the enclave

    on_behalf_of='4bf7076c-6723-49cc-b4e5-f6c6ada1bdae'  # Harold -- should it be anyone else?

    # with get_db_connection() as con:
    #     csets: List[Dict] = [dict(x) for x in sql_query(con, 'SELECT * FROM rxnorm_med_cset;')]
    #     for cset in csets:
    try:
      response: Dict[str, Union[Response, List[Response]]] = upload_new_container_with_concepts(
        on_behalf_of=on_behalf_of,
        concept_set_name=cset_name,
        intention='RxNorm medication concept sets from data liaisons.',
        research_project='RP-4A9E27',
        assigned_sme='4bf7076c-6723-49cc-b4e5-f6c6ada1bdae',
        assigned_informatician='4bf7076c-6723-49cc-b4e5-f6c6ada1bdae',
        versions_with_concepts=[{
          'omop_concepts': [{'concept_id': cid,
                             'includeDescendants':False,
                             'includeMapped':False,
                             'isExcluded':False,
                             } for cid in concept_ids],
          'on_behalf_of': on_behalf_of,
          'provenance': f'RxNorm CUIs related to: {str(rxcui)}',
          'concept_set_name': cset_name,
          # todo: fill these fields out
          'annotation': '',
          'limitations': '',
          'intention': 'RxNorm medication concept sets from data liaisons.',
          'intended_research_project': 'RP-4A9E27',
        }],
        validate_first=True,
        fail_if_exists=False)
      print(response)
    except Exception as err:
      print(err)
    cset_id = response['upload_new_cset_version_with_concepts']['properties']['codesetId']
    # todo: do this next to upload?
    #  # TODO: @Siggie will continue this to populate additional derived tables that need to be populated
    with get_db_connection() as con:
        cset_container_and_version_enclave_to_db(con, cset_name, cset_id)


if __name__ == '__main__':
  get_med_csets()


