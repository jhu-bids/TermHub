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
          , cr.relationship_id
          , c2.vocabulary_id AS vocabulary_id_2
          , cr.concept_id_2
          , c2.concept_name AS concept_name_2
  FROM {{schema}}concept_relationship cr
  JOIN concept c1 ON cr.concept_id_1 = c1.concept_id -- AND c1.invalid_reason IS NULL
  JOIN concept c2 ON cr.concept_id_2 = c2.concept_id -- AND c2.invalid_reason IS NULL
                --AND c2.standard_concept IS NOT NULL
);

CREATE INDEX crp_idx1 ON {{schema}}concept_relationship_plus(concept_id_1);

CREATE INDEX crp_idx2 ON {{schema}}concept_relationship_plus(concept_id_2);

CREATE INDEX crp_idx3 ON {{schema}}concept_relationship_plus(concept_id_1, concept_id_2);

CREATE INDEX crp_idx4 ON {{schema}}concept_relationship_plus(concept_code);

CREATE INDEX crp_idx5 ON {{schema}}concept_relationship_plus(relationship_id);

CREATE INDEX crp_idx6 ON {{schema}}concept_relationship_plus(concept_name_1);

CREATE INDEX crp_idx7 ON {{schema}}concept_relationship_plus(concept_name_2);