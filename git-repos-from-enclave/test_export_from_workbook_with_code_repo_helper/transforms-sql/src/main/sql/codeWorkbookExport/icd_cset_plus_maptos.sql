-- icd_cset_plus_maptos:  [HCUP] Diabetes mellitus with complication (v1)
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/icd_cset_plus_maptos` AS
SELECT DISTINCT
          bc.concept_set_name
        , bc.bundles
        , it.codeset_id
        --, it.codeset_id AS cid_check
        --, cr.concept_code AS concept_code_
        , it.code AS source_concept_code
        --, cr.vocabulary_id_1 AS source_vocab
        --, it.concept_id AS source_concept_id  THIS IS ACTUALLY THE TARGET CID!!!
        , cr.concept_id_1 AS source_concept_id
        , cr.concept_name_1 AS source_concept_name
        , cr.relationship_id
--        , cr.vocabulary_id_2 AS mapto_vocab
        , cr.concept_id_2 AS mapto_concept_id
        , cr.concept_name_2 AS mapto_concept_name
        , ARRAY(it.includeDescendants, it.includeMapped, it.isExcluded) AS incl_desc_mapped_exclude
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/ConceptSetBulkImportCsvFiles/processed/concept_set_version_items_rv_edited_mapped` AS it
JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/bundled_csets` bc ON it.codeset_id = bc.codeset_id
LEFT JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/concept_relationship_plus` AS cr ON it.code = cr.concept_code AND it.codeSystem = cr.vocabulary_id_1 AND cr.relationship_id = 'Maps to'
--LEFT JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/concept_relationship_plus` AS cr ON it.concept_id = cr.concept_id_1 AND cr.relationship_id = 'Maps to'
WHERE it.codeset_id = 915573730