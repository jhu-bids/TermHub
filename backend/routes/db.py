"""DB routes
    A bunch are elsewhere, but just starting this file for a couple new ones
    (2023-05-08)
"""
from functools import cache
from typing import List, Union
from fastapi import APIRouter, Query
from backend.db.queries import get_concepts
from backend.db.utils import sql_query, sql_query_single_col, get_db_connection, sql_in
from backend.utils import JSON_TYPE, get_timer, pdump, return_err_with_trace

router = APIRouter(
    # prefix="/oak",
    # tags=["oak", "ontology-access-kit],
    # dependencies=[Depends(get_token_header)],  # from FastAPI example
    responses={404: {"description": "Not found"}},
)


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
def get_concepts_route(id: List[int] = Query(...), table:str='concepts_with_counts') -> List:
    """expect list of concept_ids. using 'id' for brevity"""
    return get_concepts(concept_ids=id, table=table)


@router.post("/concepts")
@return_err_with_trace
def get_concepts_post_route(concept_ids: List[str], table:str='concepts_with_counts') -> List:
    """expect list of codeset_ids. using 'id' for brevity"""
    return get_concepts(concept_ids=concept_ids, table=table)


@router.post("/concept-ids-by-codeset-id")
@router.get("/concept-ids-by-codeset-id")
@return_err_with_trace
def get_concept_ids_by_codeset_id(codeset_ids: Union[List[str], None] = None) -> List:
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
@return_err_with_trace
def get_codeset_ids_by_concept_id(concept_ids: List[str]) -> List:
    with get_db_connection() as con:
        q = f"""
              SELECT *
              FROM codeset_ids_by_concept_id
              WHERE concept_id {sql_in(concept_ids)};"""
        rows: List = sql_query(con, q)
        return [r['codeset_ids'] for r in rows]


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


def ad_hoc_test_1():
    """Misc test"""
    terms = ['Renal failure', 'Cyst of kidney']


if __name__ == '__main__':
    ad_hoc_test_1()
