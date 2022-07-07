-- bundled_csets
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/bundled_csets` AS
SELECT  COLLECT_SET(bundle.tag_name) AS bundles
        , cs.concept_set_name
        , cs.codeset_id
        , cs.is_draft
        , cs.version
        , cs.is_most_recent_version
        , cs.provenance
        , cs.authoritative_source
        , cs.created_at
FROM `/N3C Export Area/Concept Set Ontology/Concept Set Ontology/hubble_base/code_sets` cs
LEFT JOIN `/UNITE/[Experimental] Concept Set Bundles/Concept Set Bundle Items_edited` bundle ON cs.codeset_id = bundle.best_version_id
GROUP BY 2,3,4,5,6,7,8,9