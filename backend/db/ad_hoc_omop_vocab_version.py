"""Ad hoc script: to populate omopVocabVersion in the database

Inteded for single use, 2023/11/07"""
from datetime import datetime
from typing import Dict, List

from jinja2 import Template

from backend.db.utils import get_db_connection, refresh_any_dependent_tables, run_sql
from enclave_wrangler.objects_api import fetch_all_csets


# COALESCE was another option. What is the advantage?
sql_jinja = """
UPDATE n3c.code_sets
SET omop_vocab_version = CASE
    {% for k, v in key_vals.items() %}
      WHEN codeset_id = {{k}} THEN '{{v}}'
    {% endfor %}
END
WHERE codeset_id IN ({{id_list}});"""


def populate_omop_vocab_version(update_code_sets=False, update_derived_tables=False):
    """Populate omopVocabVersion in the database.

    Since this is an ad hoc script meant only to be run once, defaulted params to False after successfully running.
    :param update_code_sets (bool): Update the code_sets table.
    :param update_derived_tables (bool): Updates derived tables."""
    if update_code_sets:
        print('Fetching all csets')  # 15 seconds
        t0 = datetime.now()
        csets: List[Dict] = fetch_all_csets()
        key_vals = {x['codesetId']: x['omopVocabVersion'] for x in csets}
        t1 = datetime.now()
        print(f' - completed in {(t1 - t0).seconds} seconds')

        print('Updating code_sets')  # 2 seconds
        query: str = Template(sql_jinja).render(
            key_vals=key_vals,
            id_list=', '.join([str(x) for x in key_vals.keys()]))
        with get_db_connection() as con:
            run_sql(con, query)
        t2 = datetime.now()
        print(f' - completed in {(t2 - t1).seconds} seconds')
    if update_derived_tables:
        # Even though 'csets_to_ignore' is a depdendent derived table which will not actually include this field and
        # thus does not need updating, I'm going to refresh all dependent tables to future-proof this in case we need to
        # repurpose / reuse.
        print('Updating derived tables')  # 1 seconds
        t0 = datetime.now()
        with get_db_connection() as con:
            refresh_any_dependent_tables(con, ['code_sets'])
        t1 = datetime.now()
        print(f' - completed in {(t1 - t0).seconds} seconds')


populate_omop_vocab_version()
