-- Column data types ---------------------------------------------------------------------------------------------------
-- TODO: Add double line breaks between each per our convention for DDL file statements?
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN project_id TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN assigned_informatician TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN assigned_sme TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN intention TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN n3c_reviewer TYPE text;
ALTER TABLE IF EXISTS {{schema}}test_concept_set_container ALTER COLUMN project_id TYPE text;
ALTER TABLE IF EXISTS {{schema}}test_concept_set_container ALTER COLUMN assigned_informatician TYPE text;
ALTER TABLE IF EXISTS {{schema}}test_concept_set_container ALTER COLUMN assigned_sme TYPE text;
ALTER TABLE IF EXISTS {{schema}}test_concept_set_container ALTER COLUMN intention TYPE text;
ALTER TABLE IF EXISTS {{schema}}test_concept_set_container ALTER COLUMN n3c_reviewer TYPE text;

-- throwing this in here for now
CREATE OR REPLACE FUNCTION array_sort (ANYARRAY)
RETURNS ANYARRAY LANGUAGE SQL
AS $$
SELECT ARRAY(SELECT unnest($1) ORDER BY 1)
$$;