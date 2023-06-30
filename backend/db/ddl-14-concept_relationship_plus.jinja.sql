-- Table: cset_members_items -------------------------------------------------------------------------------------------

DROP TABLE IF EXISTS {{schema}}concept_ids_by_codeset_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}concept_ids_by_codeset_id{{optional_suffix}} AS
SELECT codeset_id, array_agg(concept_id ORDER BY concept_id) concept_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX IF NOT EXISTS cbc_idx1{{optional_index_suffix}} ON {{schema}}concept_ids_by_codeset_id{{optional_suffix}}(codeset_id);

DROP TABLE IF EXISTS {{schema}}codeset_ids_by_concept_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}codeset_ids_by_concept_id{{optional_suffix}} AS
SELECT concept_id, array_agg(codeset_id ORDER BY codeset_id) codeset_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX IF NOT EXISTS cbc_idx2{{optional_index_suffix}} ON {{schema}}concept_ids_by_codeset_id{{optional_suffix}}(codeset_id);