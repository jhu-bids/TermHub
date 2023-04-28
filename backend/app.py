"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Set
from functools import wraps, cache
# from lru import LRU
# import pickle

import uvicorn
import urllib.parse
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.engine import LegacyRow, RowMapping

from backend.utils import JSON_TYPE, get_timer, pdump, return_err_with_trace
from backend.routes import cset_crud, oak
from backend.db.utils import get_db_connection, sql_query, SCHEMA, sql_query_single_col, sql_in
from backend.db.queries import get_concepts
from enclave_wrangler.objects_api import get_n3c_recommended_csets, enclave_api_call_caller, get_codeset_json, \
        get_expression_items, items_to_atlas_json_format
from enclave_wrangler.utils import make_objects_request
from enclave_wrangler.config import RESEARCHER_COLS
from enclave_wrangler.models import convert_rows

PROJECT_DIR = Path(os.path.dirname(__file__)).parent
# CON: using a global connection object is probably a terrible idea, but shouldn't matter much until there are multiple
# users on the same server
APP = FastAPI()
APP.include_router(cset_crud.router)
APP.include_router(oak.router)
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)
CON = get_db_connection()


# CACHE_FILE = "cache.pickle"
#
#
# def load_cache(maxsize):
#     try:
#         with open(CACHE_FILE, "rb") as f:
#             return pickle.load(f)
#     except (FileNotFoundError, pickle.UnpicklingError):
#         return LRU(maxsize)
#
# def save_cache(cache):
#     with open(CACHE_FILE, "wb") as f:
#         pickle.dump(cache, f)
#
#
# @APP.on_event("shutdown")
# async def save_cache_on_shutdown():
#     save_cache(cache)
#
#
# def memoize(maxsize=1000):
#     # TODO: allow passing in CACHE_FILE and maxsize
#     cache = load_cache(maxsize)
#
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#
#             # to prevent TypeError: unhashable type: 'list' :
#             t = tuple('|'.join([str(x) for x in a]) if type(a) == list else a for a in args)
#
#             key = (t, tuple(sorted(kwargs.items())))
#
#             if key in cache:
#                 return cache[key]
#             result = func(*args, **kwargs)
#             cache[key] = result
#             return result
#         return wrapper
#     return decorator
#
# cache = memoize(maxsize=1000)

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


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


# Database functions ---------------------------------------------------------------------------------------------------
def get_concept_set_member_ids(
    codeset_ids: List[int], columns: Union[List[str], None] = None, column: Union[str, None] = None, con=CON
) -> Union[List[int], List[LegacyRow]]:
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
    res: List[LegacyRow] = sql_query(con, query, debug=False)
    if column:  # with single column, don't return List[Dict] but just List(<column>)
        res: List[int] = [r[0] for r in res]
    return res


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
    rows: List[LegacyRow] = sql_query(
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


def get_researchers(ids: Set[str], fields: List[str] = None) -> JSON_TYPE:
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
    res: List[RowMapping] = sql_query(CON, query, {'id': list(ids)}, return_with_keys=True)
    res2 = {r['multipassId']: dict(r) for r in res}
    for _id in ids:
        if _id not in res2:
            res2[_id] = {"multipassId": _id, "name": "unknown", "emailAddress": _id}
    return res2


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
    codeset_ids: List[int] = None, selected_concept_ids: List[int] = None, con=CON, verbose=True
) -> List[Dict]:
    """Get information about concept sets related to those selected by user"""
    timer = get_timer('   get_related_csets')
    verbose and timer('get_concept_set_member_ids')
    if codeset_ids and not selected_concept_ids:
        selected_concept_ids = get_concept_set_member_ids(codeset_ids, column='concept_id')
    verbose and timer('query concept_set_members')
    query = """
    SELECT DISTINCT codeset_id
    FROM concept_set_members
    WHERE concept_id = ANY(:concept_ids)
    """
    related_codeset_ids = sql_query_single_col(con, query, {'concept_ids': selected_concept_ids}, )
    # if any selected codesets don't have concepts, they will be missing from query above
    # add them back in:
    related_codeset_ids = list(set.union(set(codeset_ids), set(related_codeset_ids)))
    verbose and timer('get_csets')
    related_csets = get_csets(related_codeset_ids)
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
    t1 = datetime.now()
    verbose and timer('done')
    return related_csets


def get_cset_members_items(codeset_ids: List[int] = None, con=CON) -> List[LegacyRow]:
    """Get concept set members items for selected concept sets
        returns:
        ...
        item: True if its an expression item, else false
        csm: false if not in concept set members
    """
    return sql_query(
        con, f"""
        SELECT *
        FROM cset_members_items
        WHERE codeset_id = ANY(:codeset_ids)
        """,
        {'codeset_ids': codeset_ids})


def get_parent_children_map(root_cids: List[int], cids: List[int], con=CON) -> Dict[int, List[int]]:
    """New hierarchy info from sql"""
    # int(x): Prevents SQL injection by throwing error if not an integer
    root_cids: List[int] = [int(x) for x in root_cids]
    cids: List[int] = [int(x) for x in cids]
    # root_cids: str = ', '.join([str(x) for x in root_cids]) or 'NULL'
    # cids: str = ', '.join([str(x) for x in cids]) or 'NULL'
    query = f"""
        SELECT *
        FROM concept_ancestor
        WHERE ancestor_concept_id {sql_in(root_cids)}
          AND descendant_concept_id {sql_in(cids)}
          AND min_levels_of_separation > 0
        ORDER BY ancestor_concept_id, min_levels_of_separation
        """
    # query = query.replace(':root_cids', root_cids).replace(':cids', cids)
    relationships: List[Dict] = [dict(x) for x in sql_query(con, query, return_with_keys=True)]
    direct_relationships: List[Dict] = [
        x for x in relationships if x['min_levels_of_separation'] == 1 and x['max_levels_of_separation'] == 1]
    parent_children_map: Dict[int, List[int]] = {}
    for x in direct_relationships:
        parent_children_map.setdefault(x['ancestor_concept_id'], []).append(x['descendant_concept_id'])
    return parent_children_map


def hierarchy(root_cids: List[int], selected_concept_ids: List[int]) -> (Dict[int, Union[Dict, None]], List[int]):
    """Get hierarchy of concepts in selected concept sets
    :returns: (i) Dict: Hierarchy, (ii) List: Orphans"""
    parent_children_map: Dict[int, List[int]] = get_parent_children_map(root_cids, selected_concept_ids)
    added_count: Dict[int, int] = {}

    def recurse(ids: List[int]):
        """Recursively build hierarchy
        Requires variables in outer scope: (i) parent_children_map, (ii) added_count
        Side effects: (i) updates added_count"""
        if not ids:
            return None
        x = {}
        for i in ids:
            children = parent_children_map.get(i, [])
            x[i] = recurse(children)
            added_count[i] = added_count.get(i, 0) + 1
        return x

    d: Dict[int, Union[Dict, None]] = recurse(root_cids)

    # Remove duplicate trees at root
    for _id, count in added_count.items():
        if count > 1:
            try:
                del d[_id]
            except KeyError:
                pass

    orphans: List[int] = list(set(selected_concept_ids) - set(added_count.keys()))

    return d, orphans


def get_concept_relationships(cids: List[int], reltypes: List[str] = ['Subsumes'], con=CON) -> List[LegacyRow]:
    """Get concept_relationship rows for cids
    """
    return sql_query(
        con, f"""
        SELECT DISTINCT *
        FROM concept_relationship_plus
        WHERE (concept_id_1 {sql_in(cids)} OR concept_id_2 {sql_in(cids)})
          AND relationship_id {sql_in(reltypes, quote_items=True)}
        """, debug=True)


junk = """  -- retaining hierarchical query (that's not working, for possible future reference)
-- example used in http://127.0.0.1:8080/backend/old_cr-hierarchy_samples/cr-hierarchy-example1.json
-- 411456218|40061425|484619125|419757429       -- 40061425 doesn't seem to exist
-- 411456218,40061425,484619125,419757429
WITH RECURSIVE hier(concept_id_1, concept_id_2, path, depth) AS (
    SELECT concept_id_1,
          concept_id_2,
          CAST(concept_id_1 AS text) || '-->' || CAST(concept_id_2 AS text) AS path,
          0 AS depth
    FROM concept_relationship
    WHERE concept_id_1 IN ( -- top level cids for 8 codeset_ids above
        45946655, 3120383, 3124992, 40545247, 3091356, 3099596, 3124987, 40297860, 40345759, 45929656, 3115991,
        40595784, 44808268, 3164757, 40545248, 45909769,
        45936903, 40545669, 45921434, 45917166, 4110177, 3141624, 40316548, 44808238, 4169883,
        45945309, 3124228, 40395876, 3151089, 40316547, 40563017, 44793048
        -- ...
    )
    UNION
    SELECT cr.concept_id_1,
            cr.concept_id_2,
            hier.path || '-->' || CAST(cr.concept_id_2 AS text) AS path,
            hier.depth + 1
    FROM concept_relationship cr
    JOIN hier ON cr.concept_id_1 = hier.concept_id_2
    WHERE hier.depth < 2
)
SELECT DISTINCT path, depth
FROM hier
ORDER BY path;
"""


def child_cids(concept_id: int, con=CON) -> List[Dict]:
    """Get child concept ids"""
    # selected_concept_ids = get_concept_set_member_ids([concept_id])
    cids = sql_query_single_col(
        con, f"""
        SELECT DISTINCT concept_id_2
        FROM concept_relationship cr
        WHERE cr.concept_id_1 = ANY(:concept_ids)
          AND cr.relationship_id = 'Subsumes'
        """,
        {'concept_id': concept_id})
    return cids


def get_all_csets(con=CON) -> Union[Dict, List]:
    """Get all concept sets"""
    results = sql_query(
        con, f""" 
        SELECT codeset_id,
              concept_set_version_title,
              concepts
        FROM {SCHEMA}.all_csets""")
    if len(set(results)) != len(results):
        raise "Duplicate records in all_csets. Please alert app admin: sigfried@sigfried.org"
    return results
    # smaller = DS2.all_csets[['codeset_id', 'concept_set_version_title', 'concepts']]
    # return smaller.to_dict(orient='records')


# Routes ---------------------------------------------------------------------------------------------------------------
@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list


@APP.get("/get-all-csets")
def _get_all_csets() -> Union[Dict, List]:
    """Route for: get_all_csets()"""
    return get_all_csets()


# TODO: the following is just based on concept_relationship
#       should also check whether relationships exis/{CONFIG["db"]}?charset=utf8mb4't in concept_ancestor
#       that aren't captured here
# TODO: Add concepts outside the list of codeset_ids?
#       Or just make new issue for starting from one cset or concept
#       and fanning out to other csets from there?
@APP.get("/selected-csets")
def _get_csets(codeset_ids: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: get_csets()"""
    requested_codeset_ids = parse_codeset_ids(codeset_ids)
    return get_csets(requested_codeset_ids)


@APP.get("/related-csets")
def _get_related_csets(codeset_ids: Union[str, None] = Query(default=''), ) -> List[Dict]:
    """Route for: get_related_csets()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    return get_related_csets(codeset_ids)


@APP.get("/cset-members-items")
def _cset_members_items(codeset_ids: Union[str, None] = Query(default=''), ) -> List[LegacyRow]:
    """Route for: cset_memberss_items()"""
    codeset_ids: List[int] = parse_codeset_ids(codeset_ids)
    return get_cset_members_items(codeset_ids)


@APP.get("/hierarchy")
def _hierarchy(
    root_cids: List[int], selected_concept_ids: List[int] = Query(default='')
) -> Dict[int, Union[Dict, None]]:
    """Route for: hierarchy()"""
    h, orphans = hierarchy(root_cids, selected_concept_ids)
    return h


@APP.get("/get-concept_relationships")
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


@APP.get("/get-n3c-recommended-codeset_ids")
def get_n3c_recommended_codeset_ids() -> Dict[int, Union[Dict, None]]:
    codeset_ids = get_n3c_recommended_csets()
    return codeset_ids


FLAGS = ['includeDescendants','includeMapped','isExcluded']
@APP.get("/cset-download")
def cset_download(codeset_id: int, csetEditState: str = None,
                  atlas_items=True, atlas_items_only=False,
                  sort_json: bool = False) -> Dict:
    """Download concept set"""
    if not atlas_items_only: # and False  TODO: document this param and what it does (what does it do again?)
        jsn = get_codeset_json(codeset_id) #  , use_cache=False)
        if sort_json:
            jsn['items'].sort(key=lambda i: i['concept']['CONCEPT_ID'])
        return jsn

    items = get_expression_items(codeset_id)
    if csetEditState:
        edits = json.loads(csetEditState)
        edits = edits[str(codeset_id)]

        deletes = [i['concept_id'] for i in edits.values() if i['stagedAction'] in ['Remove', 'Update']]
        items = [i for i in items if i['conceptId'] not in deletes]
        adds: List[Dict] = [i for i in edits.values() if i['stagedAction'] in ['Add', 'Update']]
        # items is object api format but the edits from the UI are in dataset format
        # so, convert the edits to object api format for consistency
        for item in adds:
            for flag in FLAGS:
                if flag not in item:
                    item[flag] = False;
        adds = convert_rows('concept_set_version_item',
                            'omopConceptSetVersionItem',
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


@APP.get("/enclave-api-call/{name}")
@APP.get("/enclave-api-call/{name}/{params}")
def enclave_api_call(name: str, params: Union[str, None]=None) -> Dict:
    """
    Convenience endpoint to avoid all the boilerplate of having lots of api call function
    """
    params = params.split('|') if params else []
    return enclave_api_call_caller(name, params) # .json() have the individual functions return the json

# TODO: get back to how we had it before RDBMS refactor
@APP.get("/cr-hierarchy")
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
    concept_ids: List[int] = get_concept_set_member_ids(codeset_ids, column='concept_id')
    cset_members_items = get_cset_members_items(codeset_ids)

    # this was redundant
    # concept_ids = list(set([i['concept_id'] for i in cset_members_items]))

    items = [mi for mi in cset_members_items if mi['item']]
    item_concept_ids = list(set([i['concept_id'] for i in items]))

    verbose and timer('hierarchy')
    # hierarchy --------
    h, orphans = hierarchy(item_concept_ids, concept_ids)
    # nh = new_hierarchy(root_cids=item_concept_ids, cids=concept_ids)
    # h = hierarchy(selected_concept_ids=concept_ids)

    # TODO: Fix: concepts missing from hierarchy that shouldn't be:
    # hh = json.dumps(h)
    # hierarchy_concept_ids = [int(x) for x in re.findall(r'\d+', hh)]
    # # diff for: http://127.0.0.1:8000/cr-hierarchy?rec_format=flat&codeset_ids=400614256|87065556
    # #  {4218499, 4198296, 4215961, 4255399, 4255400, 4255401, 4147509, 252341, 36685758, 4247107, 4252356, 42536648,
    # 4212441, 761062, 259055, 4235260}
    # diff = set(cset_member_ids).difference(hierarchy_concept_ids)

    # TODO: siggie was working on something here
    # o = json.load(fp)['hierarchy']
    # n = result['hierarchy']
    # print(f"o.keys() == n.keys(): {set(o.keys()) == set(n.keys())}")
    # for k,v in o.items():
    #     if not v == n[k]:
    #         print(k, o[k], n[k])
    # --------- hierarchy

    verbose and timer('related csets')
    related_csets = get_related_csets(codeset_ids=codeset_ids, selected_concept_ids=concept_ids)
    if not include_atlas_json:
        for cset in related_csets:
            del cset['atlas_json']
    selected_csets = [cset for cset in related_csets if cset['selected']]
    verbose and timer('researcher ids')
    researcher_ids = get_all_researcher_ids(related_csets)
    verbose and timer('researchers')
    researchers = get_researchers(researcher_ids)
    verbose and timer('concepts')
    concepts = [dict(c) for c in get_concepts(concept_ids)]
    for c in concepts:
        if c['concept_id'] in orphans:
            c['is_orphan'] = True
    # concept_relationships = get_concept_relationships(concept_ids)

    result = {
        # todo: Check related_csets() to see its todo's
        # 'concept_relationships': concept_relationships,
        'related_csets': related_csets,
        # todo: Check get_csets() to see its todo's
        'selected_csets': selected_csets,
        'researchers': researchers,
        'cset_members_items': cset_members_items,
        'hierarchy': h,
        # todo: concepts
        'concepts': concepts,
        # todo: frontend not making use of data_counts yet but will need
        'data_counts': [],
        'orphans': orphans,
    }
    verbose and timer('done')

    return result


@APP.get("/get-concepts")
@return_err_with_trace
def get_concepts_route(id: List[int] = Query(...), table:str='concepts_with_counts') -> List:
    return get_concepts(concept_ids=id, table=table)



if __name__ == '__main__':
    run()
