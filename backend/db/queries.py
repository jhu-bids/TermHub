"""Queries"""
from typing import List

from sqlalchemy.engine import LegacyRow

from backend.db.utils import sql_query


def get_concepts(concept_ids: List[int], con=CON, table:str='concepts_with_counts') -> List:
    """Get information about concept sets the user has selected"""
    rows: List[LegacyRow] = sql_query(
        con, f"""
          SELECT *
          FROM {table}
          WHERE concept_id {sql_in(concept_ids)};""")
    return rows


def get_all_parent_children_map(connection):
    """Get a list of tuples of all subsumption relationships in the OMOP concept_relationship table."""
    rows: List[LegacyRow] = sql_query(connection, """
        SELECT concept_id_1, concept_id_2 
        --FROM concept_relationship_subsumes_only
        FROM concept_relationship_plus
        WHERE relationship_id = 'Subsumes'
        """)

    all_parent_child_list = [(x['concept_id_1'], x['concept_id_2']) for x in rows]

    parent_children_map = {concept_id: set() for pair in all_parent_child_list for concept_id in pair}
    for parent, child in all_parent_child_list:
        parent_children_map[parent].add(child)

    return parent_children_map

