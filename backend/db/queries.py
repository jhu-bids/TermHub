"""Queries"""
from functools import cache
from typing import List, Dict, Set, Union
from fastapi import Query
from sqlalchemy import Connection

from backend.db.utils import sql_query, sql_query_single_col, get_db_connection, sql_in


def get_concepts(concept_ids: Union[List[int], Set[int]], con: Connection = None, table:str='concepts_with_counts') -> List:
    """Get information about concept sets the user has selected"""
    conn = con if con else get_db_connection()
    q = f"""
          SELECT *
          FROM {table}
          WHERE concept_id {sql_in(concept_ids)};"""
    rows: List = sql_query(conn, q)
    if not con:
        conn.close()
    return rows


def get_vocab_of_concepts(id: List[int] = Query(...), con: Connection = None, table:str='concept') -> List:
    """Expecting only one vocab for the list of concepts"""
    conn = con if con else get_db_connection()
    q = f"""
          SELECT DISTINCT vocabulary_id
          FROM {table}
          WHERE concept_id {sql_in(id)};"""
    vocabs: List = sql_query_single_col(conn, q)
    if not con:
        conn.close()
    if len(vocabs) > 1:
        raise RuntimeError(f"can only handle concepts from a single vocabulary at a time (for now). Got {', '.join(vocabs)}")
    return vocabs[0]


def get_vocabs_of_concepts(id: List[int] = Query(...), con: Connection = None, table:str='concept') -> Dict:
    """Return dict of {vocab: concept_id list}"""
    conn = con if con else get_db_connection()
    q = f"""
          SELECT vocabulary_id, array_agg(concept_id) AS concept_ids
          FROM {table}
          WHERE concept_id {sql_in(id)}
          GROUP BY 1 ORDER BY 1
          """
    vocabs: List = sql_query(conn, q)
    if not con:
        conn.close()
    return dict(vocabs)
