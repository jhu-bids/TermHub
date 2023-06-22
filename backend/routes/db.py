"""DB routes
    A bunch are elsewhere, but just starting this file for a couple new ones
    (2023-05-08)
"""
from functools import cache
from typing import List
from fastapi import APIRouter, Query
from backend.db.queries import get_concepts
from backend.db.utils import sql_query, sql_query_single_col, get_db_connection
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


@cache
@router.get("/get-concepts")
@return_err_with_trace
def get_concepts_route(id: List[int] = Query(...), table:str='concepts_with_counts') -> List:
    return get_concepts(concept_ids=id, table=table)


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
