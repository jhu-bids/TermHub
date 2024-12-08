"""Ad hoc work for CompLOINC: Get patient & record counts for all LOINC terms."""
from typing import Dict, List

import pandas as pd

from backend.db.utils import get_db_connection, sql_query


with get_db_connection() as conn:
    qry1 = """SELECT concept_code as id, 
       concept_name as label, 
       domain_id, 
       concept_class_id, 
       standard_concept, 
       domain_cnt as n_domain, 
       distinct_person_cnt as n_distinct_person,
       total_cnt as n_total_records
    FROM n3c.concepts_with_counts 
    WHERE vocabulary_id = 'LOINC' 
    -- ORDER BY total_cnt DESC, domain_cnt DESC, id ASC -- Was gonna add more cols too, but too slow. Do in Python.
    """
    rows: List[Dict] = [dict(x) for x in sql_query(conn, qry1)]

df = pd.DataFrame(rows).sort_values(["n_total_records", "n_distinct_person", "n_domain", "id"],
    ascending=[False, False, False, True])
df.to_csv("~/Desktop/loinc_n3c_counts.tsv", index=False, sep="\t")
