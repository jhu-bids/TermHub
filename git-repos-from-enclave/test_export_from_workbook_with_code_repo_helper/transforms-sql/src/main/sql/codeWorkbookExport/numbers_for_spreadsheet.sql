-- single_nodesc
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/numbers_for_spreadsheet` AS
WITH 
  sn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE NOT multimap AND is_mapto) -- single_nodesc
, sd AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE NOT multimap)              -- single_desc  
, mn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap AND is_mapto)     -- multi_nodesc 
, md AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap)                  -- multi_desc   
, mi AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap AND in_isect)     -- multi_isect  
, tn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE is_mapto)                  -- total_nodesc 
, td AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids`)                                 -- total_desc   
, ti AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE in_isect)                  -- total_isect  
, nc AS ( -- get codes (mapto_groups) with no intersecting descendants:
          SELECT ARRAY_SORT(COLLECT_SET(mapto_group)) groups
          FROM (SELECT mapto_group FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants`
                  EXCEPT
                SELECT mapto_group FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants` WHERE NOT is_mapto) x)

SELECT ARRAY_JOIN(FLATTEN(ARRAY(sn, sd, mn, md, mi1, nc, mi2, pc, tn, td, ti)), '\t') AS nums
FROM  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS sn ) AS sn
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS sd ) AS sd
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS mn ) AS mn
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS md ) AS md 
JOIN  (SELECT ARRAY('descendant_concept_id'                        ) AS mi1) AS mi1
JOIN  (SELECT ARRAY('groups'                                       ) AS nc ) AS nc
JOIN  (SELECT ARRAY(                         'person_id', 'rec_cnt') AS mi2) AS mi2
JOIN  (SELECT ARRAY('person_cnt'           , 'icd_cids ', 'rec_cnt') AS pc ) AS pc  -- all postco terms only
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS tn ) AS tn
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS td ) AS td
JOIN  (SELECT ARRAY('descendant_concept_id', 'person_id', 'rec_cnt') AS ti ) AS ti
UNION
SELECT ARRAY_JOIN(FLATTEN(ARRAY(sn, sd, mn, md, mi1, nc, mi2, pc, tn, td, ti)), '\t') AS nums
FROM  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS sn  FROM        sn) AS sn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS sd  FROM        sd) AS sd
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS mn  FROM        mn) AS mn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS md  FROM        md) AS md
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id)                                         ) AS mi1 FROM        mi) AS mi1
JOIN  (SELECT ARRAY(COUNT(DISTINCT groups)                                                        ) AS nc  FROM        nc) AS nc
JOIN  (SELECT ARRAY(                                       COUNT(DISTINCT person_id), SUM(rec_cnt)) AS mi2 FROM        mi) AS mi2
JOIN  (SELECT ARRAY(               icd_cids,                              person_cnt,     rec_cnt)  AS pc  FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/postcoord_counts`) AS pc -- all postco terms only
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS tn  FROM        tn) AS tn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS td  FROM        td) AS td
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS ti  FROM        ti) AS ti

/*  this is working --- trying to add column names to help with pasting to spreadsheet
WITH 
  sn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE NOT multimap AND is_mapto) -- single_nodesc
, sd AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE NOT multimap)              -- single_desc  
, mn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap AND is_mapto)     -- multi_nodesc 
, md AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap)                  -- multi_desc   
, mi AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE multimap AND in_isect)     -- multi_isect  
, tn AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE is_mapto)                  -- total_nodesc 
, td AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids`)                                 -- total_desc   
, ti AS (SELECT DISTINCT person_id, descendant_concept_id, rec_cnt FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/cids_and_pids` WHERE in_isect)                  -- total_isect  
, nc AS ( -- get codes (mapto_groups) with no intersecting descendants:
          SELECT ARRAY_SORT(COLLECT_SET(mapto_group)) groups
          FROM (SELECT mapto_group FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants`
                  EXCEPT
                SELECT mapto_group FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants` WHERE NOT is_mapto) x)

SELECT ARRAY_JOIN(FLATTEN(ARRAY(sn, sd, mn, md1, nc, md2, /* pc, * / mi, tn, td, ti)), '\t') AS nums
FROM  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS sn  FROM sn) AS sn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS sd  FROM sd) AS sd
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS mn  FROM mn) AS mn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id)                                         ) AS md1 FROM md) AS md1
JOIN  (SELECT ARRAY(COUNT(DISTINCT groups)                                                        ) AS nc  FROM nc) AS nc
JOIN  (SELECT ARRAY(                                       COUNT(DISTINCT person_id), SUM(rec_cnt)) AS md2 FROM md) AS md2

JOIN  (SELECT ARRAY(person_cnt, icd_cids, rec_cnt) FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/postcoord_counts`) AS pc -- all postco terms only

JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS mi FROM mi) AS mi
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS tn FROM tn) AS tn
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS td FROM td) AS td
JOIN  (SELECT ARRAY(COUNT(DISTINCT descendant_concept_id), COUNT(DISTINCT person_id), SUM(rec_cnt)) AS ti FROM ti) AS ti
*/