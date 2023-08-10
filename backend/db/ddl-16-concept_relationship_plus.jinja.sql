-- Table: concept_relationship_plus ------------------------------------------------------------------------------------
-- takes a long time to build
-- using concept_relationship_plus not just for convenience in debugging now but also
-- single source of truth for concept_relationship in termhub. quit using concept_relationship
-- and concept_relationship_subsumes_only in queries.
-- for now, due to bug (https://github.com/jhu-bids/TermHub/issues/191 and https://github.com/jhu-bids/TermHub/pull/190)
-- filtering out cr records including invalid concepts. this is probably not the right thing to do
-- in the long term, but should fix bug and let us move forward with immediate need to get pilot started (2022-01-4)
DROP TABLE IF EXISTS {{schema}}concept_relationship_plus CASCADE;

CREATE TABLE IF NOT EXISTS {{schema}}concept_relationship_plus AS (
  SELECT    c1.vocabulary_id AS vocabulary_id_1
          , cr.concept_id_1
          , c1.concept_name AS concept_name_1
          , c1.concept_code
          , c1.total_cnt AS total_cnt_1,
          , cr.relationship_id
          , c2.vocabulary_id AS vocabulary_id_2
          , cr.concept_id_2
          , c2.concept_name AS concept_name_2
          , c1.total_cnt AS total_cnt_1,
  FROM {{schema}}concept_relationship cr
  JOIN concepts_with_counts c1 ON cr.concept_id_1 = c1.concept_id -- AND c1.invalid_reason IS NULL
  JOIN concepts_with_counts c2 ON cr.concept_id_2 = c2.concept_id -- AND c2.invalid_reason IS NULL
                --AND c2.standard_concept IS NOT NULL
);

CREATE INDEX crp_idx1{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_id_1);

CREATE INDEX crp_idx2{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_id_2);

CREATE INDEX crp_idx3{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_id_1, concept_id_2);

CREATE INDEX crp_idx4{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_code);

CREATE INDEX crp_idx5{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(relationship_id);

CREATE INDEX crp_idx6{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_name_1);

CREATE INDEX crp_idx7{{optional_index_suffix}} ON {{schema}}concept_relationship_plus(concept_name_2);

DROP TABLE IF EXISTS concept_ancestor_plus CASCADE;

CREATE TABLE IF NOT EXISTS concept_ancestor_plus AS (
    SELECT
          c1.vocabulary_id AS vocabulary_id_a
        , ca.ancestor_concept_id
        , c1.concept_name AS concept_name_a
        , c1.concept_class_id AS concept_class_id_a
        , c1.total_cnt AS total_cnt_a
        -- , ca.min_levels_of_separation
        , c2.vocabulary_id AS vocabulary_id_d
        , ca.descendant_concept_id
        , c2.concept_name AS concept_name_d
        , c2.total_cnt AS total_cnt_d
        , c2.concept_class_id AS concept_class_id_d
    FROM concept_ancestor ca
    JOIN concepts_with_counts c1 ON ca.ancestor_concept_id = c1.concept_id -- AND c1.invalid_reason IS NULL
    JOIN concepts_with_counts c2 ON ca.descendant_concept_id = c2.concept_id -- AND c2.invalid_reason IS NULL
);
CREATE INDEX cap_idx1 ON concept_ancestor_plus(ancestor_concept_id);

CREATE INDEX cap_idx2 ON concept_ancestor_plus(descendant_concept_id);
