"""Temp analysis to see if these csets contain at least 1 missing concept

45492135 was a missing concept of cset 1000016833, but that is not one of these csets that is not expanding. I thought
it was. Surprisingly, that issues  is not related to the issue of these not expanding.
"""
from typing import Dict, List, Set

from backend.db.utils import get_db_connection, sql_in, sql_query


# problem_csets: List of cset_id's that are not expanding; printed from the fetch_failures_0_members.py
problem_csets = [1000011135, 1000020788, 1000027123, 1000039519, 1000049121, 1000052447, 1000054029, 1000055554,
    1000059738, 1000060169, 1000073696, 1000078840, 1000081348, 1000091334]
# cset_concept_misses: List of cset's concept expressions are missing from the concept table
cset_concept_misses: Dict[int, Set[int]] = {}

with get_db_connection() as con:
    for cset_id in problem_csets:
        expressions: List[Dict] = [dict(x) for x in sql_query(
            con, f'SELECT * FROM n3c.concept_set_version_item WHERE codeset_id = {cset_id};')]
        expression_ids: List[int] = [x['concept_id'] for x in expressions]
        concept_entries: List[Dict] = [dict(x) for x in sql_query(
            con, f'SELECT * FROM n3c.concept WHERE concept_id {sql_in(expression_ids)};')]
        concept_ids = [x['concept_id'] for x in concept_entries]
        cset_concept_misses[cset_id] = set(expression_ids) - set(concept_ids)
        print()
print()
