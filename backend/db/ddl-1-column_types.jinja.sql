-- Column data types ---------------------------------------------------------------------------------------------------
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN project_id TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN assigned_informatician TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN assigned_sme TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN intention TYPE text;
ALTER TABLE {{schema}}concept_set_container ALTER COLUMN n3c_reviewer TYPE text;
ALTER TABLE IF EXISTS test_{{schema}}concept_set_container ALTER COLUMN project_id TYPE text;
ALTER TABLE IF EXISTS test_{{schema}}concept_set_container ALTER COLUMN assigned_informatician TYPE text;
ALTER TABLE IF EXISTS test_{{schema}}concept_set_container ALTER COLUMN assigned_sme TYPE text;
ALTER TABLE IF EXISTS test_{{schema}}concept_set_container ALTER COLUMN intention TYPE text;
ALTER TABLE IF EXISTS test_{{schema}}concept_set_container ALTER COLUMN n3c_reviewer TYPE text;