/*
would like to know for each cid whether it's in the original mapto, in the union, in the intersection
adding is_maptos_only

input cols: ("mapto_group","mapto_concept_ids","multimap","mapto_concept_id","descendant_concept_id","is_mapto")
*/
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/descendants_in_isect` AS
SELECT    mapto_group
        , mapto_concept_ids
        , multimap
        , descendant_concept_id
        , is_mapto
        , ARRAY_SORT(COLLECT_SET(mapto_concept_id)) AS mapto_ancestors              -- all maptos with this descendant_concept_id
        , ARRAY_SORT(COLLECT_SET(mapto_concept_id)) = mapto_concept_ids AS in_isect -- is descendant of all maptos
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants` cids
GROUP BY 1,2,3,4,5