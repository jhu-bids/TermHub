"""DB routes
    A bunch are elsewhere, but just starting this file for a couple new ones
    (2023-05-08)
"""
from fastapi import APIRouter, Query, Request
import json
from typing import Dict, List, Union, Set, Optional
from functools import cache
import urllib.parse

from sqlalchemy import Connection
from sqlalchemy.engine import RowMapping

from backend.api_logger import Api_logger
from backend.utils import get_timer, return_err_with_trace
from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col, sql_in, run_sql
from backend.db.queries import get_concepts
from enclave_wrangler.objects_api import get_n3c_recommended_csets, enclave_api_call_caller, \
    get_concept_set_version_expression_items, items_to_atlas_json_format
from enclave_wrangler.utils import make_objects_request, whoami
from enclave_wrangler.config import RESEARCHER_COLS
from enclave_wrangler.models import convert_rows
# from backend.routes import graph
from backend.db.refresh import refresh_db


JSON_TYPE = Union[Dict, List]

router = APIRouter(
    # prefix="/oak",
    # tags=["oak", "ontology-access-kit],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)



# Database functions ---------------------------------------------------------------------------------------------------


# TODO
#  i. Keys in our old `get_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'rid', 'selected', 'created_at_container', 'created_at_version'
#   , 'intention_container', 'researchers', 'intention_version', 'created_by_container', 'intersecting_concepts',
#   'recall', 'status_version', 'created_by_version']
#  ii. Keys in our new `get_csets` that were not there previously:
#   ['created_at', 'container_intention', 'all_csets', 'created_by', 'container_created_at', 'status', 'intention',
#   'container_status', 'container_created_by']
#  fixes:
#       probably don't need precision etc.
#       switched _container suffix on duplicate col names to container_ prefix
#       joined OMOPConceptSet in the all_csets ddl to get `rid`
def get_csets(codeset_ids: List[int], con: Connection = None) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    con = con if con else get_db_connection()
    rows: List = sql_query(
        con, """
          SELECT *
          FROM all_csets
          WHERE codeset_id = ANY(:codeset_ids);""",
        {'codeset_ids': codeset_ids})
    # {'codeset_ids': ','.join([str(id) for id in requested_codeset_ids])})
    row_dicts = [dict(x) for x in rows]
    for row in row_dicts:
        row['researchers'] = get_row_researcher_ids_dict(row)

    return row_dicts


def get_row_researcher_ids_dict(row: Dict):
    """
        dict of id: [roles]
        was: {role1: id1, role2: id2, role3: id2} # return {col: row[col] for col in RESEARCHER_COLS if row[col]}
        switched to {id1: [role1], id2: [role2, role3]}
    """
    roles = {}
    for col in RESEARCHER_COLS:
        role = row[col]
        if not role:
            continue
        if role not in roles:
            roles[row[col]] = []
        roles[row[col]].append(col)
    return roles


def get_all_researcher_ids(rows: List[Dict]) -> Set[str]:
    """Get researcher ids"""
    return set([r[c] for r in rows for c in RESEARCHER_COLS if r[c]])


# TODO
#  i. Keys in our old `related_csets` that are not there anymore:
#   ['precision', 'status_container', 'concept_set_id', 'selected', 'created_at_container', 'created_at_version',
#   'intention_container', 'intention_version', 'created_by_container', 'intersecting_concepts', 'recall',
#   'status_version', 'created_by_version']
#  ii. Keys in our new `related_csets` that were not there previously:
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention',
#   'container_status', 'container_created_by']
#  see fixes above. i think everything here is fixed now
# TODO: Performance: takes ~75sec on http://127.0.0.1:8000/cr-hierarchy?format=flat&codeset_ids=400614256|87065556
def get_related_csetsOBSOLETE(  # not calling this from front end anymore. can remove tests
    codeset_ids: List[int] = None, selected_concept_ids: List[int] = None,
    include_atlas_json=False, con: Connection = None, verbose=True
) -> List[Dict]:
    """Get information about concept sets related to those selected by user"""
    con = con if con else get_db_connection()
    timer = get_timer('   get_related_csets')
    verbose and timer('get_concept_set_member_ids')
    if codeset_ids and not selected_concept_ids:
        selected_concept_ids = get_cset_members_items(codeset_ids, column='concept_id')
    verbose and timer('query concept_set_members')
    query = f"""
    SELECT DISTINCT codeset_id
    FROM concept_set_members
    WHERE concept_id {sql_in(selected_concept_ids)}
    """
    related_codeset_ids = sql_query_single_col(con, query, {'concept_ids': selected_concept_ids}, )
    # if any selected codesets don't have concepts, they will be missing from query above
    # add them back in:
    related_codeset_ids = list(set.union(set(codeset_ids), set(related_codeset_ids)))
    verbose and timer('get_csets')
    related_csets = get_csets(related_codeset_ids)
    if not include_atlas_json:
        for cset in related_csets:
            del cset['atlas_json']
    selected_cids = set(selected_concept_ids)
    selected_cid_cnt = len(selected_concept_ids)
    # this loop takes some time
    verbose and timer(f"get_concept_set_member_ids {len(related_csets)} times")
    for cset in related_csets:
        cset['selected'] = cset['codeset_id'] in codeset_ids
        cids = get_concept_set_member_ids([cset['codeset_id']], column='concept_id')
        if selected_cid_cnt and len(cids):
            intersecting_concepts = set(cids).intersection(selected_cids)
            cset['intersecting_concepts'] = len(intersecting_concepts)
            cset['recall'] = cset['intersecting_concepts'] / selected_cid_cnt
            cset['precision'] = cset['intersecting_concepts'] / len(cids)
    verbose and timer('done')
    return related_csets


def get_cset_members_items(
    codeset_ids: List[int] = [],
    columns: Union[List[str], None] = None,
    column: Union[str, None] = None,
) -> Union[List[int], List]:
    """Get concept set members items for selected concept sets
        returns:
        ...
        item: True if its an expression item, else false
        csm: false if not in concept set members
    """
    if column:
        # should check that column names are valid columns in concept_set_members
        # but probably never use this option anyway
        columns = [column]
    if not columns:
        columns = ['*']
        # columns = ['codeset_id', 'concept_id']

    with get_db_connection() as con:
        query = f"""
            SELECT DISTINCT {', '.join(columns)}
            FROM cset_members_items
            WHERE codeset_id {sql_in(codeset_ids)}
        """
        rows: List = sql_query(con, query, debug=False, return_with_keys=True)
        if column:  # with single column, don't return List[Dict] but just List(<column>)
            rows: List[int] = [r[column] for r in rows]

        rows: List = sql_query(con, query)
        return rows


# TODO: don't keep both these routes; redundant
@router.get("/cset-members-items")
def _cset_members_items(codeset_ids: Union[str, None] = Query(default=''), ) -> List:
    """Route for: cset_memberss_items()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    return get_cset_members_items(codeset_ids)


@router.get("/get-cset-members-items")
async def _get_cset_members_items(request: Request,
                                  codeset_ids: str,
                                  columns: Union[List[str], None] = Query(default=None),
                                  column: Union[str, None] = Query(default=None),
                                  # extra_concept_ids: Union[int, None] = Query(default=None)
                                  ) -> Union[List[int], List]:
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'codeset_ids': requested_codeset_ids})

    try:
        rows = get_cset_members_items(requested_codeset_ids, columns, column)
        await rpt.finish(rows=len(rows))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return rows

def get_concept_set_member_ids(
    codeset_ids: List[int],
    columns: Union[List[str], None] = None,
    column: Union[str, None] = None,
    con: Connection = None
) -> Union[List[int], List]:
    """Get concept set members"""
    con = con if con else get_db_connection()
    if column:
        columns = [column]
    if not columns:
        columns = ['codeset_id', 'concept_id']

    # should check that column names are valid columns in concept_set_members
    query = f"""
        SELECT DISTINCT {', '.join(columns)}
        FROM concept_set_members csm
        WHERE csm.codeset_id {sql_in(codeset_ids)}
    """
    res: List = sql_query(con, query, debug=False)
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        res: List[int] = [r[column] for r in res]
    return res


def get_concept_relationships(cids: List[int], reltypes: List[str] = ['Subsumes'], con: Connection = None) -> List:
    """Get concept_relationship rows for cids """
    con = con if con else get_db_connection()
    return sql_query(
        con, f"""
        SELECT DISTINCT *
        FROM concept_relationship_plus
        WHERE (concept_id_1 {sql_in(cids)} OR concept_id_2 {sql_in(cids)})
          AND relationship_id {sql_in(reltypes, quote_items=True)}
        """, debug=True)


def get_all_csets(con: Connection = None) -> Union[Dict, List]:
    """Get all concept sets"""
    con = con if con else get_db_connection()
    results = sql_query(
        con, f"""
        SELECT codeset_id,
              --concept_set_version_title,
              alias,
              version,
              --concepts
              counts,
              distinct_person_cnt,
              total_cnt
        FROM {SCHEMA}.all_csets""")
    # can't check for dups with json object in the results
    # if len(set(results)) != len(results):
    #     raise "Duplicate records in all_csets. Please alert app admin: sigfried@sigfried.org"
    return results
    # smaller = DS2.all_csets[['codeset_id', 'concept_set_version_title', 'concepts']]
    # return smaller.to_dict(orient='records')


# Routes ---------------------------------------------------------------------------------------------------------------
@router.get('/last-refreshed')
def last_refreshed_DB():
    """Check when database was last refreshed."""
    with get_db_connection() as con:
        q = """
              SELECT value
              FROM public.manage
              WHERE key = 'last_refresh_success'
            """
        results = sql_query_single_col(con, q)
        return results[0]

@cache
@router.get('/omop-id-from-concept-name/{name}')
def omop_id_from_concept_name(name):
    with get_db_connection() as con:
        q = """
          SELECT *
          FROM concept
          WHERE concept_name = (:name)
        """
        results = sql_query(con, q, {'name': name})
        return results

@router.get("/concepts")
@return_err_with_trace
async def get_concepts_route(request: Request, id: List[str] = Query(...), table:str='concepts_with_counts') -> List:
    """expect list of concept_ids. using 'id' for brevity"""
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'concept_ids': id})

    try:
        rows = get_concepts(concept_ids=id, table=table)
        await rpt.finish(rows=len(rows))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return rows


@router.post("/concepts")
async def get_concepts_post_route(request: Request, id: Union[List[str], None] = None,
                            table: str = 'concepts_with_counts') -> List:
    return await get_concepts_route(request, id=id, table=table)


@router.post("/concept-ids-by-codeset-id")
async def get_concept_ids_by_codeset_id_post(request: Request, codeset_ids: Union[List[int], None] = None) -> Dict:
    print(codeset_ids)
    return await get_concept_ids_by_codeset_id(request, codeset_ids)


@router.get("/concept-ids-by-codeset-id")
@return_err_with_trace
async def get_concept_ids_by_codeset_id(request: Request, codeset_ids: Union[List[str], None] = Query(...)) -> Dict:
    if not codeset_ids:
        return [[]]

    rpt = Api_logger()
    await rpt.start_rpt(request, params={'codeset_ids': codeset_ids})

    with get_db_connection() as con:
        try:
            q = f"""
                  SELECT csids.codeset_id, COALESCE(cibc.concept_ids, ARRAY[]::integer[]) AS concept_ids
                  FROM (VALUES{",".join([f"({csid})" for csid in codeset_ids])}) AS csids(codeset_id)
                  LEFT JOIN concept_ids_by_codeset_id cibc ON csids.codeset_id = cibc.codeset_id"""
            rows: List = sql_query(con, q)
            await rpt.finish(rows=len(rows))
        except Exception as e:
            await rpt.log_error(e)
            raise e
    return {r['codeset_id']: r['concept_ids'] for r in rows}


@router.post("/codeset-ids-by-concept-id")
@return_err_with_trace
async def get_codeset_ids_by_concept_id_post(request: Request, concept_ids: Union[List[int], None] = None) -> Dict:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'concept_ids': concept_ids})
    with get_db_connection() as con:
        try:
            q = f"""
                  SELECT *
                  FROM codeset_ids_by_concept_id
                  WHERE concept_id {sql_in(concept_ids)};"""
            rows: List = sql_query(con, q)
            await rpt.finish(rows=len(rows))
        except Exception as e:
            await rpt.log_error(e)
            raise e

    return {r['concept_id']: r['codeset_ids']  for r in rows}


@router.get("/codeset-ids-by-concept-id")
async def get_codeset_ids_by_concept_id(request: Request, concept_ids: Union[List[str], None] = Query(...)) -> Dict:
    return await get_codeset_ids_by_concept_id_post(request, concept_ids)


@router.get("/get-all-csets")
def _get_all_csets() -> Union[Dict, List]:
    """Route for: get_all_csets()"""
    return get_all_csets()



@router.get("/get-csets")
async def _get_csets(request: Request, codeset_ids: Union[str, None] = Query(default=''),
               include_atlas_json = False) -> List[Dict]:
    """Route for: get_csets()"""
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'codeset_ids': requested_codeset_ids})

    try:
        csets = get_csets(requested_codeset_ids)
        await rpt.finish(rows=len(csets))
    except Exception as e:
        await rpt.log_error(e)
        raise e

    if not include_atlas_json:
        for cset in csets:
            del cset['atlas_json']
    return csets


@router.get("/researchers")
def get_researchers(id: List[str] = Query(...), fields: Union[List[str], None] = []) -> JSON_TYPE:
    """Get researcher info for list of multipassIds.
    fields is the list of fields to return from researcher table; defaults to * if None."""
    if fields:
        fields = ', '.join([f'"{x}"' for x in fields])
    else:
        fields = '*'

    query = f"""
        SELECT {fields}
        FROM researcher
        WHERE "multipassId" = ANY(:id)
    """
    res: List[RowMapping] = sql_query(get_db_connection(), query, {'id': list(id)}, return_with_keys=True)
    res2 = {r['multipassId']: dict(r) for r in res}
    for _id in id:
        if _id not in res2:
            res2[_id] = {"multipassId": _id, "name": "unknown", "emailAddress": _id}
    return res2


@router.get("/db-refresh")
def db_refresh_route():
    """Triggers refresh of the database
    todo: May want to change this back to GH action for reasons:
     1. Easier to check logs
     If there's a problem, I can go to the actions tab and find easily. Finding on azure takes many more clicks, and then I have to scroll up to find where the refresh got logged, and it may be mixed with logs for other requests.
     2. Almost always won't increase speed of refresh
     This was supposed to be the only benefit of calling it directly.
     If someone creates a cset and clicks the button, it doesn't matter that our backend is faster than a GH action starting up, since it will take 20-45 minutes for that cset to be ready anyway. so effectively this is not faster, except for fetching csets that are not brand new, which (i) is not the primary thing people are using the button for, and (ii) is unlikely to happen w/ a fast refresh rate.
     3. Harder to make changes
     If we want to make changes to the refresh, we have to redeploy the whole app to make that work, rather than pushing to develop.
     4. Uses more server resources.
     5. Possible server stability issues
     I'm not sure, but I wonder if there is some edge case where an error that happens during the refresh, or other unanticipated side effects, could have an effect on performance or stability of the web server."""
    # response: Response = call_github_action('refresh-db')
    # return response
    refresh_db()


FLAGS = ['includeDescendants', 'includeMapped', 'isExcluded']
@router.get("/cset-download")
def cset_download(codeset_id: int, csetEditState: str = None,
                  atlas_items=True, # atlas_items_only=False,
                  sort_json: bool = False, include_metadata = False) -> Dict:
    """Download concept set
        NO LONGER USED BECAUSE WE DON'T EDIT EXISTING CODESETS BUT JUST CREATE NEW ONES FROM DEFINITIONS

    """
    # if not atlas_items_only: # and False  TODO: document this param and what it does (what does it do again?)
    #     jsn = get_codeset_json(codeset_id) #  , use_cache=False)
    #     if sort_json:
    #         jsn['items'].sort(key=lambda i: i['concept']['CONCEPT_ID'])
    #     return jsn

    items = get_concept_set_version_expression_items(codeset_id, return_detail='full', handle_paginated=True)
    items = [i['properties'] for i in items]
    if csetEditState:
        edits = json.loads(csetEditState)
        edits = edits[str(codeset_id)]

        deletes = [i['concept_id'] for i in edits.values() if i['stagedAction'] in ['Remove', 'Update']]
        items = [i for i in items if i['conceptId'] not in deletes]
        adds: List[Dict] = [i for i in edits.values() if i['stagedAction'] in ['Add', 'Update']]
        # items is object api format but the edits from the UI are in dataset format
        # so, convert the edits to object api format for consistency
        for item in adds:
            # set flags to false if they don't appear in item
            for flag in FLAGS:
                if flag not in item:
                    item[flag] = False
        adds = convert_rows('concept_set_version_item',
                            'OmopConceptSetVersionItem',
                            adds)
        items.extend(adds)
    if sort_json:
        items.sort(key=lambda i: i['conceptId'])

    # if include_metadata:

    if atlas_items:
        items_jsn = items_to_atlas_json_format(items)
        return {'items': items_jsn}
    else:
        return items  #  when would we want this?
    # pdump(items)
    # pdump(items_jsn)


# NOT USING THESE TWO ROUTES EITHER -- WAS EASIER JUST TO IMPLEMENT ON FRONTEND
#   but might want them someday
@router.post('/atlas-json-from-defs')
def atlas_json_from_defs(defs: List[Dict]) -> Dict:

    items = convert_rows('concept_set_version_item',
                        'OmopConceptSetVersionItem',
                        defs)

    items_jsn = items_to_atlas_json_format(items)
    return {'items': items_jsn}


@router.get('/atlas-json-from-defs')
def _atlas_json_from_defs(defStr: List[Dict]) -> Dict:
    defs = json.loads(defStr)
    return atlas_json_from_defs(defs)


@router.get('/omop-id-from-concept-name/{name}')
def omop_id_from_concept_name(name):
    with get_db_connection() as con:
        q = """
          SELECT *
          FROM concept
          WHERE concept_name = (:name)
        """
        results = sql_query(con, q, {'name': name})
        return results


# Utility functions ----------------------------------------------------------------------------------------------------
@cache
def parse_codeset_ids(qstring) -> List[int]:
    """Parse codeset_ids which are a | delimited string"""
    if not qstring:
        return []
    requested_codeset_ids = qstring.split('|')
    requested_codeset_ids = [int(x) for x in requested_codeset_ids]
    return requested_codeset_ids


@cache
def get_container(concept_set_name):
    """This is for getting the RID of a dataset. This is available via the ontology API, not the dataset API.
    TODO: This needs caching, but the @cache decorator is not working."""
    return make_objects_request(f'objects/OMOPConceptSetContainer/{urllib.parse.quote(concept_set_name)}')


@router.get('/whoami')
def _whoami():
    return whoami()


# @router.get('/test-auth')     # ended up using front end auth instead of this
# def test_auth():
#     # https://unite.nih.gov/workspace/developer-console/app/ri.third-party-applications.main.application.e2074643-b399-46ef-82bb-ae403a298a6a/sdk/install?packageType=pypi&language=Python
#
#     # in order to get this to work for deployment, we need to follow directions here
#     #   https://unite.nih.gov/workspace/developer-console/app/ri.third-party-applications.main.application.e2074643-b399-46ef-82bb-ae403a298a6a/docs/guide/getting-started
#     import os
#     from termhub_sdk import FoundryClient
#     from termhub_sdk.core.api import UserTokenAuth
#
#     # auth = UserTokenAuth(hostname="https://unite.nih.gov", token=os.environ["FOUNDRY_SDK_AUTH_TOKEN"])
#     auth = UserTokenAuth(hostname="https://unite.nih.gov", token=get_auth_token())
#
#     client = FoundryClient(auth=auth, hostname="https://unite.nih.gov")
#
#     ResearcherObject = client.default.objects.Researcher
#     obj = ResearcherObject.take(1)[0]
#     print(obj)
#     return {
#         'user': obj.name,
#         'email': obj.email_address,
#         'multipassId': obj.multipass_id,
#         'orcid_id': obj.orcid_id,
#         'institution': obj.institution,
#     }
#
# @router.websocket("/test-ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept() # Accept the WebSocket connection
#
#     try:
#         # Simulate a long-running process by using a loop
#         for i in range(1, 11):
#             await websocket.send_text(f"Status update {i}/10") # Send a status update to the client
#             time.sleep(1) # Simulate a long-running task
#
#         await websocket.send_text("Process completed") # Notify the client that the process is complete
#     except Exception as e:
#         await websocket.send_text(f"Error: {str(e)}") # Notify the client of any errors
#     finally:
#         await websocket.close() # Close the WebSocket connection
# """One solution: Use a decorator to poll for the disconnect"""


@router.get("/get-n3c-recommended-codeset_ids")
def get_n3c_recommended_codeset_ids() -> Dict[int, Union[Dict, None]]:
    codeset_ids = get_n3c_recommended_csets()
    return codeset_ids

@router.get("/n3c-recommended-report")
def n3c_recommended_report(as_json=False) -> Union[List[str], Dict]:

    # just for this one function
    from fastapi.responses import StreamingResponse
    import io
    import pandas as pd

    codeset_ids = get_n3c_recommended_csets()
    q = f"""
            SELECT
                  ac.is_most_recent_version,
                  ac.codeset_id, ac.concept_set_name, ac.alias,
                  CAST(ac.codeset_created_at AS DATE) AS created_at,
                  r.name AS created_by,
                  -- ac.counts::text AS counts,
                  CAST(ac.counts->>'Expression items' AS INT) AS definition_concepts,
                  CAST(ac.counts->>'Member only' AS INT) AS expansion_concepts,
                  ac.distinct_person_cnt,
                  COUNT(distinct cs.codeset_id) AS versions
            FROM all_csets ac
            JOIN code_sets cs ON ac.concept_set_name = cs.concept_set_name
            JOIN researcher r ON ac.codeset_created_by = r."multipassId"
            WHERE ac.codeset_id {sql_in(codeset_ids)}
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
            ORDER BY 1, 6, 5, 4
    """
    rows = sql_query(get_db_connection(), q)
    if (as_json):
        return rows
    else:
        df = pd.DataFrame(rows, columns=['is_most_recent_version', 'codeset_id',
                                         'concept_set_name', 'alias', 'created_at', 'created_by'])
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv" )
        response.headers["Content-Disposition"] = "attachment; filename=n3c-recommended-report.csv"
        return response


@router.get("/n3c-comparison-rpt")
def _n3c_comparison_rpt():
    return n3c_comparison_rpt()


# @cache
def n3c_comparison_rpt():
    with get_db_connection() as con:
        rpt = sql_query_single_col(con, "SELECT rpt FROM public.codeset_comparison WHERE rpt IS NOT NULL")
    return rpt


@cache
def get_comparison_rpt(con, codeset_id_1: int, codeset_id_2: int) -> Dict[str, Union[str, None]]:
    cset_1 = get_csets([codeset_id_1])[0]
    cset_2 = get_csets([codeset_id_2])[0]

    cset_1_only = sql_query(con, """
        SELECT 'removed ' || concept_id || ' ' || concept_name AS diff FROM (
            SELECT concept_id, concept_name FROM concept_set_members WHERE codeset_id = :codeset_id_1
            EXCEPT
            SELECT concept_id, concept_name FROM concept_set_members WHERE codeset_id = :cset_2_codeset_id
        ) x
    """, {'codeset_id_1': codeset_id_1, 'cset_2_codeset_id': codeset_id_2})
    # orig_only = [dict(r) for r in orig_only]
    cset_1_only = [dict(r)['diff'] for r in cset_1_only]

    cset_2_only = sql_query(con, """
        SELECT 'added ' || concept_id || ' ' || concept_name AS diff FROM (
            SELECT concept_id, concept_name FROM concept_set_members WHERE codeset_id = :cset_2_codeset_id
            EXCEPT
            SELECT concept_id, concept_name FROM concept_set_members WHERE codeset_id = :codeset_id_1
        ) x
    """, {'codeset_id_1': codeset_id_1, 'cset_2_codeset_id': codeset_id_2})
    # cset_2_only = [dict(r) for r in cset_2_only]
    cset_2_only = [dict(r)['diff'] for r in cset_2_only]

    diffs = cset_1_only + cset_2_only

    flag_cnts_1 = ', flags: ' + ', '.join([f'{k}: {v}' for k, v in cset_1['flag_cnts'].items()]) if  cset_1['flag_cnts'] else ''
    flag_cnts_2 = ', flags: ' + ', '.join([f'{k}: {v}' for k, v in cset_2['flag_cnts'].items()]) if  cset_2['flag_cnts'] else ''

    rpt = {
        'name': cset_1['concept_set_name'],
        'cset_1': f"{cset_1['codeset_id']} v{cset_1['version']}, vocab {cset_1['omop_vocab_version']}; {cset_1['distinct_person_cnt']} pts, {cset_1['concepts']} concepts{flag_cnts_1}",
        'cset_2': f"{cset_2['codeset_id']} v{cset_2['version']}, vocab {cset_2['omop_vocab_version']}; {cset_2['distinct_person_cnt']} pts, {cset_2['concepts']} concepts{flag_cnts_2}",
        'author': cset_1['codeset_creator'],
        'cset_1_codeset_id': codeset_id_1,
        # 'cset_1_version': cset_1['version'],
        'cset_2_codeset_id': codeset_id_2,
        # 'cset_2_version': cset_2['version'],
        # 'cset_1_only': cset_1_only,
        # 'cset_2_only': cset_2_only,
        'diffs': diffs,
    }
    return rpt


def generate_n3c_comparison_rpt():
    with get_db_connection() as con:
        pairs = sql_query(
            con,
            """
                SELECT orig_codeset_id, new_codeset_id
                FROM public.codeset_comparison
                WHERE rpt IS NULL
                """)
        i = 1
        for pair in pairs:
            pair = list(dict(pair).values())
            print(f"Processing {str(pair)} {i} of {len(pairs)}")
            i += 1

            rpt = get_comparison_rpt(con, *pair)

            run_sql(con, """
                    UPDATE public.codeset_comparison
                    SET rpt = :rpt
                    WHERE orig_codeset_id = :orig_codeset_id
                      AND new_codeset_id = :new_codeset_id
                    """, {'orig_codeset_id': pair[0],
                          'new_codeset_id': pair[1],
                          'rpt': json.dumps(rpt)})


@router.get("/next-api-call-group-id")
def next_api_call_group_id() -> int:
    with get_db_connection():
        id = sql_query_single_col(get_db_connection(), "SELECT nextval('api_call_group_id_seq')")[0]
        return id


if __name__ == '__main__':
    from backend.utils import pdump
    # n3c_comparison_rpt()
    # generate_n3c_comparison_rpt()
    pass