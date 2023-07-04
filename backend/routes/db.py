"""DB routes
    A bunch are elsewhere, but just starting this file for a couple new ones
    (2023-05-08)
"""
from fastapi import APIRouter, Query
import json
import requests
from typing import Dict, List, Union, Set
from functools import cache
import urllib.parse

from requests import Response
from sqlalchemy.engine import RowMapping
from backend.utils import JSON_TYPE, call_github_action, get_timer, return_err_with_trace
from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col, sql_in
from backend.db.queries import get_concepts
from enclave_wrangler.objects_api import get_n3c_recommended_csets, enclave_api_call_caller, get_codeset_json, \
    get_concept_set_version_expression_items, items_to_atlas_json_format
from enclave_wrangler.utils import make_objects_request
from enclave_wrangler.config import RESEARCHER_COLS
from enclave_wrangler.models import convert_rows
from backend.db.config import CONFIG
from backend.routes import graph


# CON: using a global connection object is probably a terrible idea, but shouldn't matter much until there are multiple
CON = get_db_connection()

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
#   ['created_at', 'container_intentionall_csets', 'created_by', 'container_created_at', 'status', 'intention',
#   'container_status', 'container_created_by']
#  fixes:
#       probably don't need precision etc.
#       switched _container suffix on duplicate col names to container_ prefix
#       joined OMOPConceptSet in the all_csets ddl to get `rid`
def get_csets(codeset_ids: List[int], con=CON) -> List[Dict]:
    """Get information about concept sets the user has selected"""
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
def get_related_csets(
    codeset_ids: List[int] = None, selected_concept_ids: List[int] = None,
    include_atlas_json=False, con=CON, verbose=True
) -> List[Dict]:
    """Get information about concept sets related to those selected by user"""
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


def get_cset_members_items(codeset_ids: List[int], columns: Union[List[str], None] = None,
                           column: Union[str, None] = None, con=CON ) -> Union[List[int], List]:
    """Get concept set members items for selected concept sets
        returns:
        ...
        item: True if its an expression item, else false
        csm: false if not in concept set members
    """
    if column:
        columns = [column]
    if not columns:
        columns = ['*']
        # columns = ['codeset_id', 'concept_id']

    # should check that column names are valid columns in concept_set_members
    query = f"""
        SELECT DISTINCT {', '.join(columns)}
        FROM cset_members_items
        WHERE codeset_id {sql_in(codeset_ids)}
    """
    res: List = sql_query(con, query, debug=False, return_with_keys=True)
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        res: List[int] = [r[column] for r in res]
    return res


def get_concept_set_member_ids(
    codeset_ids: List[int], columns: Union[List[str], None] = None, column: Union[str, None] = None, con=CON
) -> Union[List[int], List]:
    """Get concept set members"""
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


def get_concept_relationships(cids: List[int], reltypes: List[str] = ['Subsumes'], con=CON) -> List:
    """Get concept_relationship rows for cids """
    return sql_query(
        con, f"""
        SELECT DISTINCT *
        FROM concept_relationship_plus
        WHERE (concept_id_1 {sql_in(cids)} OR concept_id_2 {sql_in(cids)})
          AND relationship_id {sql_in(reltypes, quote_items=True)}
        """, debug=True)


def get_all_csets(con=CON) -> Union[Dict, List]:
    """Get all concept sets"""
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
def get_concepts_route(id: List[str] = Query(...), table:str='concepts_with_counts') -> List:
    """expect list of concept_ids. using 'id' for brevity"""
    return get_concepts(concept_ids=id, table=table)


@router.post("/concepts")
def get_concepts_post_route(id: Union[List[str], None] = None,
                            table: str = 'concepts_with_counts') -> List:
    return get_concepts(concept_ids=id, table=table)


@router.post("/concept-ids-by-codeset-id")
def get_concept_ids_by_codeset_id_post(codeset_ids: Union[List[int], None] = None) -> List:
    print(codeset_ids)
    return get_concept_ids_by_codeset_id(codeset_ids)


@router.get("/concept-ids-by-codeset-id")
@return_err_with_trace
def get_concept_ids_by_codeset_id(codeset_ids: Union[List[str], None] = Query(...)) -> List:
    if not codeset_ids:
        return [[]]
    with get_db_connection() as con:
        q = f"""
              SELECT csids.codeset_id, COALESCE(cibc.concept_ids, ARRAY[]::integer[]) AS concept_ids
              FROM (VALUES{",".join([f"({csid})" for csid in codeset_ids])}) AS csids(codeset_id)
              LEFT JOIN concept_ids_by_codeset_id cibc ON csids.codeset_id = cibc.codeset_id"""
        rows: List = sql_query(con, q)
        # d = {r['codeset_id']:r['concept_ids'] for r in rows}
        return [r['concept_ids'] for r in rows]


@router.post("/codeset-ids-by-concept-id")
def get_codeset_ids_by_concept_id_post(id: Union[List[int], None] = None) -> List:
    with get_db_connection() as con:
        q = f"""
              SELECT *
              FROM codeset_ids_by_concept_id
              WHERE concept_id {sql_in(id)};"""
        rows: List = sql_query(con, q)
        return [r['codeset_ids'] for r in rows]


@router.get("/codeset-ids-by-concept-id")
@return_err_with_trace
def get_codeset_ids_by_concept_id(id: Union[List[str], None] = Query(...)) -> List:
    return get_codeset_ids_by_concept_id_post(id)


@router.get("/get-all-csets")
def _get_all_csets() -> Union[Dict, List]:
    """Route for: get_all_csets()"""
    return get_all_csets()


@router.get("/get-cset-members-items")
def _get_cset_members_items(codeset_ids: str,
                            columns: Union[List[str], None] = Query(default=None),
                            column: Union[str, None] = Query(default=None)
                            ) -> Union[List[int], List]:
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    return get_cset_members_items(requested_codeset_ids, columns, column)


@router.get("/get-csets")
def _get_csets(codeset_ids: Union[str, None] = Query(default=''),
               include_atlas_json = False) -> List[Dict]:
    """Route for: get_csets()"""
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    csets = get_csets(requested_codeset_ids)
    if not include_atlas_json:
        for cset in csets:
            del cset['atlas_json']
    return csets


@router.get("/related-csets")
def _get_related_csets(codeset_ids: Union[str, None] = Query(default=''),
                       include_atlas_json = False) -> List[Dict]:
    """Route for: get_related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    return get_related_csets(codeset_ids, include_atlas_json)


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
    res: List[RowMapping] = sql_query(CON, query, {'id': list(id)}, return_with_keys=True)
    res2 = {r['multipassId']: dict(r) for r in res}
    for _id in id:
        if _id not in res2:
            res2[_id] = {"multipassId": _id, "name": "unknown", "emailAddress": _id}
    return res2


@router.get("/cset-members-items")
def _cset_members_items(codeset_ids: Union[str, None] = Query(default=''), ) -> List:
    """Route for: cset_memberss_items()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    return get_cset_members_items(codeset_ids)


@router.get("/db-refresh")
def db_refresh_route() -> Response:
    """Triggers refresh of the database"""
    response: Response = call_github_action('refresh-db')
    return response

# TODO: if using this at all, fix it to use graph.hierarchy, which doesn't need root_cids
# @router.get("/hierarchy")
# def _hierarchy(
#     root_cids: List[int], selected_concept_ids: List[int] = Query(default='')
# ) -> Dict[int, Union[Dict, None]]:
#     """Route for: hierarchy()"""
#     h, orphans = hierarchy(root_cids, selected_concept_ids)
#     return h


@router.get("/get-concept_relationships")
def _get_concept_relationships(
    codeset_ids: Union[str, None] = Query(default='')
) -> Dict[int, Union[Dict, None]]:
    """Route for: get_concept_relationships -- except that it takes codeset_ids instead of concept_ids"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    concept_ids: List[int] = get_concept_set_member_ids(codeset_ids, column='concept_id')
    cr_rows = get_concept_relationships(concept_ids)

    # just starting to try to make hierarchical list of these
    #p2c = itertools.groupby(cr_rows, lambda r: r['concept_id_1'])
    # pairs = [(r['concept_id_1'],r['concept_id_2']) for r in cr_rows]
    # p2c = itertools.groupby(pairs, lambda r: r[0])
    # d = {k:[x[1] for x in list(v)] for k,v in p2c}

    return cr_rows


@router.get("/get-n3c-recommended-codeset_ids")
def get_n3c_recommended_codeset_ids() -> Dict[int, Union[Dict, None]]:
    codeset_ids = get_n3c_recommended_csets()
    return codeset_ids


FLAGS = ['includeDescendants', 'includeMapped', 'isExcluded']
@router.get("/cset-download")
def cset_download(codeset_id: int, csetEditState: str = None,
                  atlas_items=True, atlas_items_only=False,
                  sort_json: bool = False) -> Dict:
    """Download concept set"""
    if not atlas_items_only: # and False  TODO: document this param and what it does (what does it do again?)
        jsn = get_codeset_json(codeset_id) #  , use_cache=False)
        if sort_json:
            jsn['items'].sort(key=lambda i: i['concept']['CONCEPT_ID'])
        return jsn

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
    if atlas_items:
        items_jsn = items_to_atlas_json_format(items)
        return {'items': items_jsn}
    else:
        return items  #  when would we want this?
    # pdump(items)
    # pdump(items_jsn)


@router.get("/enclave-api-call/{name}")
@router.get("/enclave-api-call/{name}/{params}")
def enclave_api_call(name: str, params: Union[str, None] = None) -> Dict:
    """
    Convenience endpoint to avoid all the boilerplate of having lots of api call function
    """
    params = params.split('|') if params else []
    return enclave_api_call_caller(name, params) # .json() have the individual functions return the json

# TODO: get back to how we had it before RDBMS refactor
@router.get("/cr-hierarchy")
@return_err_with_trace
def cr_hierarchy(include_atlas_json: bool = False, codeset_ids: Union[str, None] = Query(default=''), ) -> Dict:
    """Get concept relationship hierarchy

    Example:
    http://127.0.0.1:8000/cr-hierarchy?format=flat&codeset_ids=400614256|87065556
    """
    verbose = True
    # TODO: TEMP FOR TESTING. #191 isn't a problem with the old json data
    # fp = open(r'./backend/old_cr-hierarchy_samples/cr-hierarchy - example1 - before refactor.json')
    # return json.load(fp)

    timer = get_timer('cr-hierarchy')
    verbose and timer('members items')
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    # concept_ids: List[int] = get_concept_set_member_ids(codeset_ids, column='concept_id')
    cset_members_items = get_cset_members_items(codeset_ids)
    concept_ids = set([item['concept_id'] for item in cset_members_items])

    # this was redundant
    # concept_ids = list(set([i['concept_id'] for i in cset_members_items]))

    verbose and timer('hierarchy')
    # hierarchy --------
    # h, orphans = hierarchy(item_concept_ids, concept_ids)
    # nh = new_hierarchy(root_cids=item_concept_ids, cids=concept_ids)
    # h = hierarchy(selected_concept_ids=concept_ids)
    # h = graph.hierarchy(concept_ids)

    verbose and timer('related csets')
    related_csets = get_related_csets(codeset_ids=codeset_ids, selected_concept_ids=concept_ids,
                                      include_atlas_json=include_atlas_json)
    selected_csets = [cset for cset in related_csets if cset['selected']]
    verbose and timer('researcher ids')
    researcher_ids = get_all_researcher_ids(related_csets)
    verbose and timer('researchers')
    researchers = get_researchers(researcher_ids)
    verbose and timer('concepts')
    edges = graph.subgraph(concept_ids)

    concept_ids.update([int(e[0]) for e in edges])
    concept_ids.update([int(e[1]) for e in edges])
    concept_ids = list(concept_ids)
    concepts = [dict(c) for c in get_concepts(concept_ids)]
    # for c in concepts:
    #     if c['concept_id'] in orphans:
    #         c['is_orphan'] = True
    # concept_relationships = get_concept_relationships(concept_ids)

    result = {
        'edges': edges,
        'cset_members_items': cset_members_items,
        'selected_csets': selected_csets,
        'researchers': researchers,
        # todo: Check related_csets() to see its todo's
        # todo: Check get_csets() to see its todo's
        'related_csets': related_csets,
        'concepts': concepts,
    }
    verbose and timer('done')

    return result

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


def ad_hoc_test_1():
    """Misc test"""
    terms = ['Renal failure', 'Cyst of kidney']


if __name__ == '__main__':
    ad_hoc_test_1()
