-- Table: codeset_ids_by_concept_id ------------------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}codeset_ids_by_concept_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}codeset_ids_by_concept_id{{optional_suffix}} AS
SELECT CAST(concept_id AS bigint) concept_id,
       array_agg(CAST(codeset_id AS bigint) ORDER BY codeset_id) codeset_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX cbc_idx2{{optional_index_suffix}} ON {{schema}}codeset_ids_by_concept_id{{optional_suffix}}(concept_id);