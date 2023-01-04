"""Queries"""
from typing import List

from sqlalchemy.engine import LegacyRow

from backend.db.utils import sql_query


def get_all_parent_child_subsumes_tuples(connection):
    """Get a list of tuples of all subsumption relationships in the OMOP concept_relationship table."""
    rows: List[LegacyRow] = sql_query(connection, """
        SELECT concept_id_1, concept_id_2 
        --FROM concept_relationship_subsumes_only
        FROM concept_relationship_plus
        WHERE relationship_id = 'Subsumes'
        """)
    return [(x['concept_id_1'], x['concept_id_2']) for x in rows]
