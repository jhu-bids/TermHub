-- Table: csets_to_ignore ----------------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW {{schema}}csets_to_ignore{{optional_suffix}} AS
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