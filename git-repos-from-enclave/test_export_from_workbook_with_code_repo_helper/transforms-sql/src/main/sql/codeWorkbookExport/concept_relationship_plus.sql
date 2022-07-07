-- concept_relationship_plus
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/concept_relationship_plus` AS
SELECT    c1.vocabulary_id AS vocabulary_id_1
        , cr.concept_id_1
        , c1.concept_name AS concept_name_1
        , c1.concept_code
        , cr.relationship_id
        , c2.vocabulary_id AS vocabulary_id_2
        , cr.concept_id_2
        , c2.concept_name AS concept_name_2
FROM `/N3C Export Area/OMOP Vocabularies/concept_relationship` cr
JOIN `/N3C Export Area/OMOP Vocabularies/concept` c1 ON cr.concept_id_1 = c1.concept_id
JOIN `/N3C Export Area/OMOP Vocabularies/concept` c2 ON cr.concept_id_2 = c2.concept_id 
               AND c2.standard_concept IS NOT NULL -- was 49,187,612 rows before this condition, 
                                                   --     32,345,621 rows after
                                                   --       running again on 2022-06-07 after vocab update
