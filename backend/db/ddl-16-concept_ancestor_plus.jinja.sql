-- Table: concept_ancestor_plus ------------------------------------------------------------------------------------
-- Temp tables do not have {{optional_suffix}} for _new and _old becauser they do not get recreated during refreshes; they are temporary.
CREATE TEMP TABLE root_concepts AS (
    SELECT ancestor_concept_id FROM {{schema}}concept_ancestor r WHERE min_levels_of_separation != 0
    EXCEPT
    SELECT descendant_concept_id FROM {{schema}}concept_ancestor r WHERE min_levels_of_separation != 0
);

CREATE TEMP TABLE concept_depth AS (
    SELECT ca.descendant_concept_id, min(ca.min_levels_of_separation) AS depth
    /* from (SELECT * FROM concept_ancestor ca limit 100000) ca */
    FROM {{schema}}concept_ancestor ca
    JOIN root_concepts rc ON ca.ancestor_concept_id = rc.ancestor_concept_id
    GROUP BY 1
);
CREATE INDEX cdidx ON concept_depth(descendant_concept_id);

DROP TABLE IF EXISTS {{schema}}concept_ancestor_plus{{optional_suffix}} CASCADE;

CREATE TABLE IF NOT EXISTS {{schema}}concept_ancestor_plus{{optional_suffix}} AS (
    SELECT
          c1.vocabulary_id AS vocabulary_id_a
        , ca.ancestor_concept_id
        , c1.concept_name AS concept_name_a
        , cd.depth AS a_depth
        /*
        , c1.concept_class_id AS concept_class_id_a
        , c1.total_cnt AS total_cnt_a
        */
        , ca.min_levels_of_separation AS mls
        , c2.vocabulary_id AS vocabulary_id_d
        , ca.descendant_concept_id
        , c2.concept_name AS concept_name_d
        , c2.standard_concept AS standard_concept_b
        , c2.total_cnt AS total_cnt_d
        , c2.concept_class_id AS concept_class_id_d
    FROM {{schema}}concept_ancestor ca
    JOIN {{schema}}concepts_with_counts c1 ON ca.ancestor_concept_id = c1.concept_id -- AND c1.invalid_reason IS NULL
    JOIN {{schema}}concepts_with_counts c2 ON ca.descendant_concept_id = c2.concept_id -- AND c2.invalid_reason IS NULL
    LEFT JOIN concept_depth cd ON ca.ancestor_concept_id = cd.descendant_concept_id
);
CREATE INDEX cap_idx1{{optional_index_suffix}} ON {{schema}}concept_ancestor_plus{{optional_suffix}}(ancestor_concept_id);

CREATE INDEX cap_idx2{{optional_index_suffix}} ON {{schema}}concept_ancestor_plus{{optional_suffix}}(descendant_concept_id);
