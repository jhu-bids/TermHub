-- Table: cset_members_items -------------------------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.csets_to_ignore AS
SELECT all_csets.concept_set_name,
    all_csets.container_created_at,
    max(all_csets.codeset_created_at) AS latest,
    count(*) AS cnt
FROM all_csets
WHERE (
    lower(all_csets.concept_set_name) LIKE '%test%'::text OR
    lower(all_csets.concept_set_name) ~~ '%example%'::text
) AND (
    all_csets.concept_set_name <> ALL(
        ARRAY[
            'COVID test'::text,
            'SARS-CoV-2 test measurementSARS2 COVID2 Test from 655'::text,
            '75862-3 (HbA1C Tests)'::text])
    )
GROUP BY all_csets.concept_set_name, all_csets.container_created_at
ORDER BY (max(all_csets.codeset_created_at));

DROP TABLE IF EXISTS {{schema}}concept_ids_by_codeset_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}concept_ids_by_codeset_id{{optional_suffix}} AS
SELECT codeset_id, array_agg(concept_id ORDER BY concept_id) concept_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX IF NOT EXISTS cbc_idx1 ON {{schema}}concept_ids_by_codeset_id{{optional_suffix}}(codeset_id);

DROP TABLE IF EXISTS {{schema}}codeset_ids_by_concept_id{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}codeset_ids_by_concept_id{{optional_suffix}} AS
SELECT concept_id, array_agg(codeset_id ORDER BY codeset_id) codeset_ids
FROM {{schema}}cset_members_items
GROUP BY 1;

CREATE INDEX IF NOT EXISTS cbc_idx2 ON {{schema}}concept_ids_by_codeset_id{{optional_suffix}}(codeset_id);