-- pid_cid_rec_cnts
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/pid_cid_rec_cnts` AS
SELECT  person_id
    ,   condition_concept_id AS concept_id
    ,   condition_start_date
    ,   COUNT(*) AS rec_cnt 
FROM `/UNITE/LDS Release/datasets/condition_occurrence`
GROUP BY 1,2,3
