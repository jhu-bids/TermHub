-- Table: concept_ids_by_codeset_id ------------------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}concept_ids_by_codeset_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}concept_ids_by_codeset_id{{optional_suffix}} AS
SELECT CAST(codeset_id AS bigint) codeset_id,
       array_agg(CAST(concept_id AS bigint) ORDER BY concept_id) concept_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX cbc_idx1{{optional_index_suffix}} ON {{schema}}concept_ids_by_codeset_id{{optional_suffix}}(codeset_id);