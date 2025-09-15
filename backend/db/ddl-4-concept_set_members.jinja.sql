-- Table: concept_set_members - dedupe ---------------------------------------------------------------------------------
-- some rows in concept_set_members have been duplicates, so need to get rid of those
--  might be with import/loading errors, but just fixing it here for now
SELECT * INTO {{schema}}concept_set_members_with_dups FROM {{schema}}concept_set_members;

DROP TABLE {{schema}}concept_set_members CASCADE;

SELECT DISTINCT * INTO {{schema}}concept_set_members FROM {{schema}}concept_set_members_with_dups;

DROP TABLE {{schema}}concept_set_members_with_dups CASCADE;

-- there are version items with no corresponding row in the code_sets table!!
-- have to get rid of them
DELETE FROM {{schema}}concept_set_version_item vi
WHERE NOT EXISTS (
    SELECT * FROM {{schema}}code_sets cs WHERE cs.codeset_id = vi.codeset_id);

DELETE FROM {{schema}}concept_set_members csm
WHERE NOT EXISTS (
    SELECT * FROM {{schema}}code_sets cs WHERE cs.codeset_id = csm.codeset_id);
