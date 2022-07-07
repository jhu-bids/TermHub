/*
-- mapto_groups

trying version from https://unite.nih.gov/workspace/vector/view/ri.vector.main.workbook.ce26122b-0f83-431c-b250-186af0d541e7?branch=what+went+wrong
*/
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_groups` AS
WITH by_src_cncpt AS (
    SELECT
            mm.source_concept_code, -- no point collecting, only 1 per source_concept_id
            mm.source_concept_id,
            --mm.source_concept_name,
            ARRAY_SORT(COLLECT_SET(mm.mapto_concept_id)) AS mapto_concept_ids
    FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/icd_cset_plus_maptos` mm
    GROUP BY 1,2
)
SELECT    ROW_NUMBER() OVER (ORDER BY mapto_concept_ids) AS mapto_group
        , mapto_concept_ids
        , ARRAY_SORT(COLLECT_SET(source_concept_id)) AS source_concept_ids
        , ARRAY_SORT(COLLECT_SET(source_concept_code)) AS source_concept_codes
FROM by_src_cncpt
GROUP BY 2


/*
dataset/transform name: descendants_of_maptos
join in all descendants of the mapped to SNOMED codes

SELECT
        ARRAY_SORT(COLLECT_SET(mm.source_concept_code)) AS source_concept_codes,
        mm.source_concept_id,
        mm.source_concept_name,
        ARRAY_SORT(COLLECT_SET(mm.mapto_concept_id)) AS mapto_concept_ids,
        ARRAY_SORT(COLLECT_SET(mm.mapto_concept_name)) AS mapto_concept_names,
        ROW_NUMBER() OVER (ORDER BY source_concept_name, source_concept_id) AS mapto_group
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/icd_cset_plus_maptos` mm
GROUP BY 2, 3

*/