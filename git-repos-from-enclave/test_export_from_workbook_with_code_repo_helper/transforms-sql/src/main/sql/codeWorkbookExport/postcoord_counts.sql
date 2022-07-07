-- postcoord_counts_wip
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/postcoord_counts` AS
WITH persons_with_every_mapto_in_group_concurrent (
    SELECT  mc.mapto_group
        ,   mc.`/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids`
        ,   pc.person_id
        ,   pc.condition_start_date
        ,   ARRAY_SORT(COLLECT_SET(pc.concept_id)) AS pid_date_cids_in_group
        ,   ARRAY_EXCEPT(mc.`/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids`, COLLECT_SET(pc.concept_id)) AS missing_mapto_concept_ids
    FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids` mc
    JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/pid_cid_rec_cnts` pc ON mc.mapto_concept_id = pc.concept_id
    GROUP BY 1,2,3,4
    HAVING SIZE(ARRAY_EXCEPT(mc.`/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids`, COLLECT_SET(pc.concept_id))) = 0)
, distinct_pid_cids AS (
    SELECT  p.person_id
        ,   EXPLODE(p.`/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids`) AS concept_id
        ,   p.mapto_group  
    FROM persons_with_every_mapto_in_group_concurrent p)
, whatever AS (
    SELECT  dpc.person_id
        ,   dpc.concept_id
        ,   ARRAY_SORT(COLLECT_SET(dpc.mapto_group)) AS mapto_groups  
    FROM distinct_pid_cids dpc
    GROUP BY 1,2)
    
SELECT  SIZE(ARRAY_DISTINCT(FLATTEN(COLLECT_SET(w.mapto_groups)))) AS icd_cids /* the mapto groups correspond to the codes originally mapped from calling it icd_cids
                                                                                   because icd codes are not quite 1-to-1 with their non-standard OMOP codes */
    ,   COUNT(DISTINCT pc.concept_id) AS snomed_codes
    ,   COUNT(DISTINCT pc.person_id) AS person_cnt
    ,   COUNT(*) AS rec_cnt
    FROM whatever w
    JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/pid_cid_rec_cnts` pc ON pc.person_id = w.person_id
                                AND pc.concept_id = w.concept_id
    