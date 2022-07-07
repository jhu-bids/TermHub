/* 
-- maptocids_plus_descendants

adding person recs to each concept_id in descendants
*
* would like to know for each cid whether it's in the original mapto, in the union, and/or in the intersection
*/
CREATE TABLE `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/maptocids_plus_descendants` AS
SELECT    m2cid.*
        , ca.descendant_concept_id
        , m2cid.mapto_concept_id = ca.descendant_concept_id AS is_mapto
FROM `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/mapto_concept_ids` m2cid
LEFT JOIN `/UNITE/[RP-4A9E27] DI&H - Data Quality/post-coordinated-icd-to-snomed-concepts/datasets/concept_ancestor_plus` ca ON m2cid.mapto_concept_id = ca.ancestor_concept_id