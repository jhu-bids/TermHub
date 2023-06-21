-- Table view: cset_members_items_plus ---------------------------------------------------------------------------------
CREATE OR REPLACE VIEW {{schema}}cset_members_items_plus{{optional_suffix}} AS (
SELECT    csmi.*
        , c.vocabulary_id
        , c.concept_name
        , c.concept_code
        , c.concept_class_id
        , c.standard_concept
FROM {{schema}}cset_members_items csmi
JOIN concept c ON csmi.concept_id = c.concept_id);
-- CREATE INDEX IF NOT EXISTS csmip_idx1 ON {{schema}}cset_members_items_plus{{optional_suffix}}(codeset_id);
-- CREATE INDEX IF NOT EXISTS csmip_idx2 ON {{schema}}cset_members_items_plus{{optional_suffix}}(concept_id);
-- CREATE INDEX IF NOT EXISTS csmip_idx3 ON {{schema}}cset_members_items_plus{{optional_suffix}}(codeset_id, concept_id);