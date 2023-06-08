-- Table: concept_set_members - dedupe ---------------------------------------------------------------------------------
-- some rows in concept_set_members have been duplicates, so need to get rid of those
--  might be with import/loading errors, but just fixing it here for now
SELECT * INTO {{schema}}concept_set_members_with_dups FROM {{schema}}concept_set_members;

DROP TABLE {{schema}}concept_set_members;

SELECT DISTINCT * INTO {{schema}}concept_set_members FROM {{schema}}concept_set_members_with_dups;

DROP TABLE concept_set_members_with_dups;