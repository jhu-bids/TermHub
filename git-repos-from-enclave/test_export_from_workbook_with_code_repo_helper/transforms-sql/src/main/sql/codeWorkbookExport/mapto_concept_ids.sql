/* 
-- mapto_concept_ids

for each distinct group of mapto_concept_ids, one row for each concept_id in it
    as well as the mapto_group id it was assigned (if that ends up helping with anything),
    the list of concept_ids in the group,
    and the source concept_ids and codes mapped from that resulted in this group
    expands 142 (hcup diabetes) mapto groups into 240 rows
    
    next step will bring in descendants
*/
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids` AS
SELECT    --source_concept_ids
        --, source_concept_codes
        DISTINCT
          mapto_group
        , mapto_concept_ids
        , SIZE(mapto_concept_ids) > 1 AS multimap
        , EXPLODE(mapto_concept_ids) AS mapto_concept_id
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_groups`