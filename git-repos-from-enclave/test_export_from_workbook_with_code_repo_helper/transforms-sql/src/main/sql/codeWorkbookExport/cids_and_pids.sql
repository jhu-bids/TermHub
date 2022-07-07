--create cids_and_pids:
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` AS
SELECT    pids.person_id
        , pids.rec_cnt
        , cids.descendant_concept_id
        , cids.multimap
        , cids.is_mapto
        , cids.in_isect
        , ARRAY_SORT(COLLECT_SET(mapto_group)) AS mapto_groups
        --, mapto_concept_ids
        --, mapto_group
        -- mapto_ancestors, 
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/descendants_in_isect` cids -- (mapto_group, mapto_concept_ids, multimap, descendant_concept_id, is_mapto, mapto_ancestors, in_isect)
LEFT JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/pid_cid_rec_cnts` pids -- descendant_person_ids pids -- (descendant_concept_id, person_id, rec_cnt)
       ON cids.descendant_concept_id = pids.concept_id
GROUP BY 1,2,3,4,5,6
-- was 134,862,354 rows
--      13,745,629 rows as of 2022-06-07
--      21,018,950 rows after switching to `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/pid_cid_rec_cnts` with dates instead of condition_occurrence
  

