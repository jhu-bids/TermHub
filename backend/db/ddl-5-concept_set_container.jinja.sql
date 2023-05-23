-- Table: concept_set_container - dedupe -------------------------------------------------------------------------------
-- has duplicate records except for the created_at col. get rid of duplicates, keeping the most recent.
--  code from https://stackoverflow.com/a/28085614/1368860
--      which also has code that works for databases other than postgres, if we ever need that
WITH deduped AS (
    SELECT DISTINCT ON (concept_set_id) concept_set_id, created_at
    FROM {{schema}}concept_set_container
    ORDER BY concept_set_id, created_at DESC
)
DELETE FROM {{schema}}concept_set_container csc
WHERE NOT EXISTS (
    SELECT FROM deduped dd
    WHERE csc.concept_set_id = dd.concept_set_id
  AND csc.created_at = dd.created_at
    );