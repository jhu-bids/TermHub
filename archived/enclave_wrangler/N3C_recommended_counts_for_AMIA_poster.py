"""
This is for an AMIA poster submission:
  https://docs.google.com/document/d/1SbZlF7UzW4TAJbCf-jqG6RSJ-uEZgfaDAVYIROM3vnM/edit
Most of the code for calculating the numbers I did in a code workbook:
  https://unite.nih.gov/workspace/vector/view/ri.vector.main.workbook.0e57d248-aeaf-46c8-87ea-47b86c7bba8d?branch=master
But some data isn't available (intended domain team) or up-to-date (bundle items)
  in datasets, so I needed to use API calls
"""


from enclave_wrangler.objects_api import get_bundle_codeset_ids
from enclave_wrangler.utils import make_objects_request
# from functools import cache
from backend.utils import pdump, dump

def get_cset(codeset_id):
  return make_objects_request(f'objects/OMOPConceptSet/{codeset_id}',
    return_type='data', expect_single_item=True, verbose=False)

def get_versions(csetName):
  return make_objects_request(f'objects/OMOPConceptSetContainer/{csetName}/links/OMOPConceptSet',
                              return_type='data', expect_single_item=False, verbose=False)

def get_member_concept_ids(codeset_id):
  concepts = make_objects_request(
    f'objects/OMOPConceptSet/{codeset_id}/links/omopconcepts',
    return_type='data', expect_single_item=False, verbose=False)
  return [c['properties']['conceptId'] for c in concepts]

def get_intended_domain_teams(codeset_id):
  teams = make_objects_request(
    f'objects/OMOPConceptSet/{codeset_id}/links/intendedDomainTeam',
    return_type='data', expect_single_item=False, verbose=False)
  # return teams
  return [t['properties']['title'] for t in teams]

codeset_ids = get_bundle_codeset_ids('N3C Recommended', verbose=True)
print(codeset_ids)

total_versions = 0
all_concepts = set()

for i, codeset_id in enumerate(codeset_ids):
  teams = get_intended_domain_teams(codeset_id)
  if teams:
    print(codeset_id, teams)
  continue
  cset = get_cset(codeset_id)
  pdump(cset)
  versions = get_versions(cset['conceptSetNameOMOP'])
  pdump(versions)
  total_versions += len(versions)
  concept_ids = get_member_concept_ids(codeset_id)
  all_concepts.update(concept_ids)
  print(f'got {i+1} out of {len(codeset_ids)}')

print(versions, len(all_concepts))



# containers_ids = [x['properties']['conceptSetNameOMOP'] for x in new_csets]
print(codeset_ids)

