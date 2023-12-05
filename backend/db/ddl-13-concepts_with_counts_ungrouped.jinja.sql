-- Table view: concepts_with_counts_ungrouped --------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}concepts_with_counts_ungrouped{{optional_suffix}} CASCADE;

CREATE TABLE IF NOT EXISTS {{schema}}concepts_with_counts_ungrouped{{optional_suffix}} AS (
SELECT DISTINCT
        c.concept_id,
        c.concept_name,
        c.domain_id,
        c.vocabulary_id,
        c.concept_class_id,
        c.standard_concept,
        c.concept_code,
        c.invalid_reason,
        COALESCE(tu.total_count, 0) AS total_cnt,
        COALESCE(tu.distinct_person_count, 0) AS distinct_person_cnt,
        tu.domain
FROM {{schema}}concept c
LEFT JOIN {{schema}}deidentified_term_usage_by_domain_clamped tu ON c.concept_id = tu.concept_id);

CREATE INDEX ccu_idx1{{optional_index_suffix}} ON {{schema}}concepts_with_counts_ungrouped{{optional_suffix}}(concept_id);
--CREATE INDEX ccu_idx2{{optional_index_suffix}} ON concepts_with_counts_ungrouped(concept_id);