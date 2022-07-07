-- concept_ancestor_plus
--  78,169,566 rows
--       running again on 2022-06-07 after vocab update
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/concept_ancestor_plus` AS
SELECT    c1.vocabulary_id AS ancestor_vocabulary_id
        , ca.ancestor_concept_id
        , c1.concept_name AS ancestor_concept_name
        , ca.min_levels_of_separation
        , ca.max_levels_of_separation
        , c2.vocabulary_id AS descendant_vocabulary_id
        , ca.descendant_concept_id
        , c2.concept_name AS descendant_concept_name
FROM `/N3C Export Area/OMOP Vocabularies/concept_ancestor` ca
JOIN `/N3C Export Area/OMOP Vocabularies/concept` c1 ON ca.ancestor_concept_id = c1.concept_id
JOIN `/N3C Export Area/OMOP Vocabularies/concept` c2 ON ca.descendant_concept_id = c2.concept_id