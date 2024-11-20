"""DB routes
    A bunch are elsewhere, but just starting this file for a couple new ones
    (2023-05-08)
"""
import io
import json
import urllib.parse
from datetime import datetime
from functools import cache, lru_cache
from typing import Dict, List, Union, Set, Optional

import pandas as pd
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from psycopg2 import sql
from sqlalchemy import Connection, Row, text
from sqlalchemy.engine import RowMapping
from starlette.responses import Response

from backend.api_logger import Api_logger, get_ip_from_request, API_CALL_LOGGING_ON
from backend.db.queries import get_concepts
from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col, sql_in, sql_in_safe, run_sql
from backend.utils import return_err_with_trace, commify, recs2dicts, call_github_action
from enclave_wrangler.config import RESEARCHER_COLS
from enclave_wrangler.models import convert_rows
from enclave_wrangler.objects_api import get_n3c_recommended_csets, get_codeset_json, get_bundle_codeset_ids, \
        get_bundle_names, get_concept_set_version_expression_items, items_to_atlas_json_format, get_codeset_json
from enclave_wrangler.utils import make_objects_request, whoami, check_token_ttl

FLAGS = ['includeDescendants', 'includeMapped', 'isExcluded']
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
def get_csets(codeset_ids: List[int]) -> List[Dict]:
    """Get information about concept sets the user has selected"""
    with get_db_connection() as con:
        rows: List = sql_query(
            con, """
              SELECT *
              FROM all_csets
              WHERE codeset_id = ANY(:codeset_ids);""",
            {'codeset_ids': codeset_ids})
    row_dicts: List[Dict] = [dict(x) for x in rows]
    for row in row_dicts:
        row['researchers'] = get_row_researcher_ids_dict(row)

    return row_dicts


def identify_missing_concept_ids(concept_ids: List[int]) -> List[int]:
    """
    Parameters
    ----------
    concept_ids

    Returns
    -------

    """
    with get_db_connection() as con:
        sql = f"""
            SELECT t.concept_id
            FROM (VALUES 
                {", ".join([f"({c})" for c in concept_ids])}
            ) AS t (concept_id)
            LEFT JOIN concept c ON t.concept_id = c.concept_id
            WHERE c.concept_id IS NULL
        """
        missing_concept_ids = sql_query_single_col(con, sql)
    return missing_concept_ids


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


def get_cset_members_items(
    codeset_ids: Union[List[int], None] = None,
    columns: Union[List[str], None] = None,
    column: Union[str, None] = None,
    return_with_keys: bool = True,
) -> Union[List[int], List]:
    """Get concept set members items for selected concept sets
        returns:
        ...
        item: True if its an expression item, else false
        csm: false if not in concept set members
    """
    if column and columns:
        raise ValueError('Cannot specify both columns and column')

    with (get_db_connection() as con):
        where = f" WHERE codeset_id = ANY(:codeset_ids)"
        params = {'codeset_ids': codeset_ids or []}

        if column:
            columns = [column]

        if columns:
            select = sql.SQL("SELECT DISTINCT {}" + " FROM cset_members_items").format(
                sql.SQL(', ').join(map(sql.Identifier, columns)),
                sql.SQL(', ').join(sql.Placeholder() * len(columns)))
            # noinspection PyUnresolvedReferences false_positive
            select = select.as_string(con.connection.connection)
        else:
            select = "SELECT * FROM cset_members_items"

        query = text(select + where)

        if column:  # with single column, don't return List[Dict] but just List(<column>)
            res: List = sql_query_single_col(con, query, params)
        else:
            res: List = sql_query(con, query, params, return_with_keys=return_with_keys)

    return res


@router.get("/get-cset-members-items")
async def _get_cset_members_items(
    request: Request,
    codeset_ids: str = None,
    columns: Union[List[str], None] = Query(default=None),
    column: Union[str, None] = Query(default=None),
    return_with_keys: bool = True,
    # extra_concept_ids: Union[int, None] = Query(default=None)
):  # -> Union[List[int], List]
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'codeset_ids': requested_codeset_ids})

    try:
        rows = get_cset_members_items(requested_codeset_ids, columns, column, return_with_keys)
        await rpt.finish(rows=len(rows))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return rows


def get_concept_relationships(cids: List[int], reltypes: List[str] = ['Subsumes'], con: Connection = None) -> List:
    """Get concept_relationship rows for cids """
    conn = con if con else get_db_connection()
    result = sql_query(
        conn, f"""
        SELECT DISTINCT *
        FROM concept_relationship_plus
        WHERE (concept_id_1 {sql_in(cids)} OR concept_id_2 {sql_in(cids)})
          AND relationship_id {sql_in(reltypes, quote_items=True)}
        """, debug=True)
    if not con:
        conn.close()
    return result


def get_all_csets(con: Connection = None) -> Union[Dict, List]:
    """Get all concept sets"""
    conn = con if con else get_db_connection()
    results = sql_query(
        conn, f"""
        SELECT codeset_id,
              concept_set_version_title,
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
    if not con:
        conn.close()
    return results
    # smaller = DS2.all_csets[['codeset_id', 'concept_set_version_title', 'concepts']]
    # return smaller.to_dict(orient='records')


# Routes ---------------------------------------------------------------------------------------------------------------
@router.get('/last-refreshed')
def last_refreshed_db():
    """Check when database was last refreshed."""
    q = """
        SELECT value
        FROM public.manage
        WHERE key = 'last_refresh_success'
"""
    with get_db_connection() as con:
        results = sql_query_single_col(con, q)
    return results[0]

@cache
@router.get('/omop-id-from-concept-name/{name}')
def omop_id_from_concept_name(name):
    """Get OMOP ID for given concept name"""
    q = """
      SELECT *
      FROM concept
      WHERE concept_name = (:name)
    """
    with get_db_connection() as con:
        results = sql_query(con, q, {'name': name})
    return results

# todo: style: 'id' matches built-in name 'id'
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
async def get_concepts_post_route(
    request: Request, id: Union[List[str], None] = None, table: str = 'concepts_with_counts'
) -> List:
    """Route for get_concepts() via POST"""
    return await get_concepts_route(request, id=id, table=table)


@lru_cache(maxsize=20)  # probably not helpful, caching at front end anyway
@router.get("/concept-search")
async def _concept_search(search_str: str, sort_by: str = "-total_cnt|vocabulary_id|concept_name") -> List[int]:
    valid_sort_columns = {"total_cnt", "concept_name", "vocabulary_id", "domain_id", "concept_class_id"}
    #   for desc, prefix with -
    sort_strs = sort_by.split('|')
    sort_cols = []
    for s in sort_strs:
        desc = False
        if s[0] == '-':
            desc = True
            s = s[1:]
        if s not in valid_sort_columns:
            raise ValueError(f"invalid sort_by: {s}")
        s = f"{s} DESC" if desc else s
        sort_cols.append(s)
    q = f"""
      SELECT concept_id
      FROM concepts_with_counts
      WHERE concept_name ILIKE :search_str
      ORDER BY {', '.join(sort_cols)} DESC
    """
    with get_db_connection() as con:
        concept_ids = sql_query_single_col(con, q, { "search_str": '%' + search_str + '%', })
    return concept_ids

@router.get("/api-call-logging-on")
def api_call_logging_on() -> bool:
    return API_CALL_LOGGING_ON

@router.get("/next-api-call-group-id")
def next_api_call_group_id() -> Optional[int]:
    if not API_CALL_LOGGING_ON:
        return None

    """Get next API call group ID"""
    with get_db_connection() as con:
        id = sql_query_single_col(con, "SELECT nextval('api_call_group_id_seq')")[0]
    return id


@router.post("/related-cset-concept-counts")
def get_related_cset_concept_counts(concept_ids: List[int] = None, verbose=True) -> Dict:
    """Returns dict of codeset_id: count of included concepts"""
    query = f"""
        SELECT DISTINCT codeset_id, concept_id 
        FROM concept_set_members
        WHERE concept_id = ANY(:concept_ids)
    """
    with get_db_connection() as con:
        csm = sql_query(con, query, {'concept_ids': concept_ids}, )

    counts = {}
    for record in csm:
        codeset_id = record['codeset_id']
        counts[codeset_id] = counts.get(codeset_id, 0) + 1

    return counts


@router.get("/get-all-csets")
def _get_all_csets() -> Union[Dict, List]:
    """Route for: get_all_csets()"""
    return get_all_csets()


@router.get("/get-csets")
async def _get_csets(
    request: Request, codeset_ids: Union[str, None] = Query(default=''), include_atlas_json=False
) -> List[Dict]:
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


def get_researchers(ids: Union[str, List[str]], fields: Union[List[str], None] = []) -> Dict[str, Dict]:
    """Get researcher info for list of multipassIds.

    Fields is the list of fields to return from researcher table; defaults to * if None.
    """
    # Format params
    ids: List[str] = [ids] if isinstance(ids, str) else ids
    ids = list(ids)
    if fields:
        fields = ', '.join([f'"{x}"' for x in fields])
    else:
        fields = '*'

    query = f"""
        SELECT {fields}
        FROM researcher
        WHERE "multipassId" = ANY(:id)
    """
    with get_db_connection() as con:
        res: List[RowMapping] = sql_query(con, query, {'id': list(ids)}, return_with_keys=True)
    # todo: Allow return List[Dict] as well? if so, would basically just reutrn
    res2 = {r['multipassId']: dict(r) for r in res}
    # Add placeholder info for any researchers not presently in the database
    for _id in ids:
        if _id not in res2:
            res2[_id] = {"multipassId": _id, "name": "unknown", "emailAddress": "unknown"}
    return res2


@router.get("/researchers")
def get_researchers_route(ids: List[str] = Query(...), fields: Union[List[str], None] = []) -> JSON_TYPE:
    """Route for get_researchers()"""
    return get_researchers(ids, fields)


@router.get("/db-refresh")
def db_refresh_route():
    """Triggers refresh of the database"""
    response: Response = call_github_action('refresh-db')
    return response.status_code



FLAGS = ['includeDescendants', 'includeMapped', 'isExcluded']
@router.get("/cset-download")
def cset_download(codeset_id: int, csetEditState: str = None,
                  atlas_items=True, # atlas_items_only=False,
                  sort_json: bool = False, include_metadata = False) -> Dict:
    """Download concept set
        Had deleted this, but it's used for atlas-json download for existing concept sets
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
def get_n3c_recommended_codeset_ids():  # -> Dict[int, Union[Dict, None]]
    """Get N3C recommended codeset IDs"""
    codeset_ids = get_n3c_recommended_csets()
    return codeset_ids


@router.get("/download-n3c-recommended")
def download_n3c_recommended():
    """"
        This one is trying to get all useful cset information including definition
        It seems to work fine, but is not being used.
    """
    codeset_ids = get_n3c_recommended_csets()
    csets_from_ac = get_csets(codeset_ids)
    # researcher_ids =
    # return uniq(flatten(csets.map(cset= > Object.keys(cset.researchers))));
    csets = []
    with get_db_connection() as con:
        for codeset_id in codeset_ids:
            cset = get_codeset_json(codeset_id, con)
            csets.append(cset)
    return {'codeset_json': csets, 'codeset_metadata': csets_from_ac}


@router.get("/get-bundle-names")
def _get_bundle_names():  # -> Union[List[Row], StreamingResponse]
    return sorted(get_bundle_names())


@router.get("/n3c-recommended-report", response_model=False)
def n3c_recommended_report(as_json=False):  # -> Union[List[Row], StreamingResponse]
    return bundle_report('N3C Recommended', as_json)


@router.get("/bundle-report", response_model=False)
def bundle_report(bundle: str, as_json=False):  # -> Union[List[Row], StreamingResponse]
    """N3C recommended report

todo: possibly drop return typing, or figure out how to get it correct.
 it's not imperative that we have return typing, but this also triggers validation, which is now failing after
 upgrading pydantic. response_model=False addresses:
 fastapi.exceptions.FastAPIError: Invalid args for response field! Hint: check that typing.Union[typing.List[
 sqlalchemy.engine.row.Row], starlette.responses.StreamingResponse] is a valid Pydantic field type. If you are using
 a return type annotation that is not a valid Pydantic field (e.g. Union[Response, dict, None]) you can disable
 generating the response model from the type annotation with the path operation decorator parameter response_model
 =None. Read more: https://fastapi.tiangolo.com/tutorial/response-model/
"""
    codeset_ids = get_bundle_codeset_ids(bundle)
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
    with get_db_connection() as con:
        rows = sql_query(con, q)
    if as_json:
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
async def _n3c_comparison_rpt(request: Request):
    # TODO: figure out how to log user's IP address to maybe figure out why
    #       this endpoint keeps getting called constantly -- is there a bot out
    #       there? maybe we just block that IP? @joeflack4 -- can you help?
    ip = await get_ip_from_request(request)
    print(f"n3c-comparison-rpt call from: {ip}")
    return n3c_comparison_rpt()


# @cache
def n3c_comparison_rpt():
    """
    display comparison data compiled in generate_n3c_comparison_rpt()
        and get_comparison_rpt()
    """
    with get_db_connection() as con:
        rpt = sql_query_single_col(con, "SELECT rpt FROM public.codeset_comparison WHERE rpt IS NOT NULL")
    return rpt


@router.get("/single-n3c-comparison-rpt")
def single_n3c_comparison_rpt(pair: str):
    """
    display comparison data compiled in generate_n3c_comparison_rpt()
        and get_comparison_rpt()
    """
    orig_codeset_id, new_codeset_id = pair.split('-')
    with get_db_connection() as con:
        rpt = sql_query_single_col(
            con,
            "SELECT rpt FROM public.codeset_comparison WHERE orig_codeset_id || '-' || new_codeset_id = :pair",
            {"pair": pair})

    return rpt[0] if rpt else None


@router.post("/get-similar-concepts")
def get_similar_concepts(concept_ids: List[Union[int, str]], which: str = 'all' ) -> Dict:
    """Get similar concepts for multiple concept IDs in a single query
     Args:
        concept_ids: List of concept IDs (can be integers or strings)
        which: Relationship type filter ('all', 'to', or 'from')
    """
    concept_ids = [int(cid) for cid in concept_ids]
    if which == 'all':  # all similar for possible replacement suggestions for codeset comparisons
        rels = [
            'Maps to',
            'Maps to value',
            'Mapped from',
            'Mapped from value',
            'Concept alt_to from',
            'Concept alt_to to',
            'Concept poss_eq from',
            'Concept poss_eq to',
            'Concept replaced by',
            'Concept replaces',
            'Concept same_as from',
            'Concept same_as to',
            'Concept was_a from',
            'Concept was_a to'
        ]
    elif which == 'to': # what OHDSI includeMapped usually does, I think
        rels = [
            'Maps to',
            'Maps to value',
        ]
    elif which == 'from': # what OHDSI includeMapped should do, I think
        rels = [
            'Mapped from',
            'Mapped from value',
        ]

    with get_db_connection() as con:
        q = """
            SELECT 
                cr.concept_id_1 as source_concept_id,
                c2.concept_id,
                c2.concept_name,
                c2.vocabulary_id,
                c2.concept_class_id,
                c2.standard_concept,
                public.ARRAY_SORT(ARRAY_AGG(relationship_id)) rels
            FROM concept_relationship cr
            JOIN concepts_with_counts c2 ON cr.concept_id_2 = c2.concept_id
            WHERE concept_id_1 = ANY(:concept_ids)
              AND relationship_id = ANY(:rels)
              AND concept_id_1 != concept_id_2
            GROUP BY 1,2,3,4,5,6;
        """
        results = sql_query(con, q, {'concept_ids': list(concept_ids), 'rels': rels})

        # Organize results by source concept
        replacements_by_concept = {}
        for row in results:
            source_id = row['source_concept_id']
            if source_id not in replacements_by_concept:
                replacements_by_concept[source_id] = []
            replacement = {k: v for k, v in row.items() if k != 'source_concept_id'}
            replacements_by_concept[source_id].append(replacement)

        return replacements_by_concept


def get_comparison_rpt(codeset_id_1: int, codeset_id_2: int) -> Dict[str, Union[str, None]]:
    def enrich_records_with_concepts(records: List[dict], concepts: List[dict]) -> List[dict]:
        """Enrich records with concept information where available"""
        concept_lookup = {c['concept_id']: c for c in concepts}

        for rec in records:
            if concept := concept_lookup.get(rec['concept_id']):
                rec.update({
                    'name': concept['concept_name'],
                    'voc': concept['vocabulary_id'],
                    'cls': concept['concept_class_id'],
                    'std': concept['standard_concept']
                })
        return records

    def format_codeset_info(cset: dict) -> str:
        """Format codeset information into a readable string"""
        flag_cnts = f"flags: {', '.join(f'{k}: {v}' for k, v in cset['flag_cnts'].items())}" if cset[
            'flag_cnts'] else ''
        return (
            f"{cset['codeset_id']} v{cset['version']}, "
            f"vocab {cset['omop_vocab_version']}; "
            f"{commify(cset['distinct_person_cnt'])} pts, "
            f"{commify(cset['total_cnt'] or cset['total_cnt_from_term_usage'])} recs, "
            f"{commify(cset['concepts'])} concepts, {flag_cnts}"
        )

    # Get basic codeset information
    cset_1 = get_csets([codeset_id_1])[0]
    cset_2 = get_csets([codeset_id_2])[0]

    # Get member items for both codesets
    csmi_1 = get_cset_members_items([codeset_id_1], ['concept_id', 'csm', 'item', 'flags'])
    csmi_2 = get_cset_members_items([codeset_id_2], ['concept_id', 'csm', 'item', 'flags'])

    # Find concepts that were removed or added
    cids_1 = {c['concept_id'] for c in csmi_1}
    cids_2 = {c['concept_id'] for c in csmi_2}
    all_codeset_cids = cids_1 | cids_2

    removed_cids = cids_1 - cids_2
    added_cids = cids_2 - cids_1

    # Create record lists
    removed = [dict(csmi) for csmi in csmi_1 if csmi['concept_id'] in removed_cids]
    added = [dict(csmi) for csmi in csmi_2 if csmi['concept_id'] in added_cids]

    # Get and add concept information
    removed = enrich_records_with_concepts(removed, get_concepts(removed_cids))
    added = enrich_records_with_concepts(added, get_concepts(added_cids))

    # Get all replacement suggestions in one query
    if removed:
        all_replacements = get_similar_concepts(removed_cids)

        # Add filtered replacement suggestions for removed concepts
        for rec in removed:
            replacements = all_replacements.get(rec['concept_id'], [])
            rec['replacements'] = [
                r for r in replacements
                if r['concept_id'] not in all_codeset_cids
            ]

    return {
        'name': cset_1['concept_set_name'],
        'cset_1': format_codeset_info(cset_1),
        'cset_2': format_codeset_info(cset_2),
        'author': cset_1['codeset_creator'],
        'codeset_id_1': codeset_id_1,
        'codeset_id_2': codeset_id_2,
        'added': added,
        'removed': removed,
    }

def generate_n3c_comparison_rpt():
    """Generate N3C comparison report
        If you want more or different comparisons than what are currently in the report, you need
        to add new pairs of original and new codesets to the codeset_comparison table.
        For doing that while actually creating new copies of codesets based on old ones, look at
         make_new_versions_of_csets.
        To just add a comparison between two codeset_ids that already exist, add the new pair to the table,
        leaving the rpt column as NULL, and then run this function.
    """
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

            rpt = get_comparison_rpt(*pair)

            run_sql(con, """
                    UPDATE public.codeset_comparison
                    SET rpt = :rpt
                    WHERE orig_codeset_id = :orig_codeset_id
                      AND new_codeset_id = :new_codeset_id
                    """, {'orig_codeset_id': pair[0],
                          'new_codeset_id': pair[1],
                          'rpt': json.dumps(rpt)})


@router.get("/check-token")
def check_token() -> Dict:
    """Check Enclave authorization tokentoken"""
    w = whoami()
    # name = w.get('username', 'No name')
    t = check_token_ttl(format='date-days')
    return {'whoami': w, 'expires': t}


# todo: can / should we replace this query with selecting from `apijoin` table instead?
def usage_query(verbose=True) -> List[Dict]:
    """Query for usage data

    Filters out problematic api_call_group_id where the call group is amibiguous (-1 or NULL)"""
    t0 = datetime.now()
    with get_db_connection() as con:
        data: List[RowMapping] = sql_query(con, """SELECT * FROM public.apijoin""")
            # SELECT DISTINCT r.*, array_sort(g.api_calls) api_calls, g.duration_seconds, g.group_start_time,
            #     date_bin('1 week', timestamp::TIMESTAMP, TIMESTAMP '2023-10-30')::date week,
            #     timestamp::date date
            # FROM public.api_runs r
            # LEFT JOIN public.apiruns_grouped g ON g.api_call_group_id = r.api_call_group_id
            # WHERE g.api_call_group_id != -1 AND g.api_call_group_id IS NOT NULL;
            # -- WHERE g.api_call_group_id = -1 or g.api_call_group_id IS NULL;
            # """)
    data: List[Dict] = [dict(x) for x in data]
    if verbose:
        print(f'usage_query(): Fetched {len(data)} records in n seconds: {(datetime.now() - t0).seconds}')
    return data


@router.get("/usage")
def usage():  # -> JSON_TYPE
    """Usage report: Get all data from our monitoring."""
    return usage_query()


if __name__ == '__main__':
    generate_n3c_comparison_rpt()
