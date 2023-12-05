-- Table view: cset_members_items_plus ---------------------------------------------------------------------------------
CREATE OR REPLACE VIEW {{schema}}cset_members_items_plus{{optional_suffix}} AS (
SELECT csmi.*
        , c.concept_code
        , c.concept_name
        , c.concept_class_id
FROM {{schema}}cset_members_items csmi
JOIN concept c ON csmi.concept_id = c.concept_id);
-- CREATE INDEX csmip_idx1{{optional_index_suffix}} ON {{schema}}cset_members_items_plus{{optional_suffix}}(codeset_id);
-- CREATE INDEX csmip_idx2{{optional_index_suffix}} ON {{schema}}cset_members_items_plus{{optional_suffix}}(concept_id);
-- CREATE INDEX csmip_idx3{{optional_index_suffix}} ON {{schema}}cset_members_items_plus{{optional_suffix}}(codeset_id, concept_id);