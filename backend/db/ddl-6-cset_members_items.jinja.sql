-- Table: cset_members_items -------------------------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}cset_members_items{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}cset_members_items{{optional_suffix}} AS
SELECT
    COALESCE(csm.codeset_id, item.codeset_id) AS codeset_id,
    COALESCE(csm.concept_id, item.concept_id) AS concept_id,
    csm.codeset_id IS NOT NULL AS csm,
    item.codeset_id IS NOT NULL AS item,
    array_to_string(array_remove(ARRAY[
                                     CASE WHEN item."isExcluded" THEN 'isExcluded' ELSE NULL END,
                                     CASE WHEN item."includeDescendants" THEN 'includeDescendants' ELSE NULL END,
                                     CASE WHEN item."includeMapped" THEN 'includeMapped' ELSE NULL END ],
                                 NULL), ',') AS item_flags,
    item."isExcluded",
    item."includeDescendants",
    item."includeMapped"
FROM {{schema}}concept_set_members csm
FULL OUTER JOIN {{schema}}concept_set_version_item item
ON csm.codeset_id = item.codeset_id
    AND csm.concept_id = item.concept_id
WHERE csm.codeset_id IS NOT NULL
   OR item.codeset_id IS NOT NULL;

CREATE INDEX csmi_idx1 ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id);

CREATE INDEX csmi_idx2 ON {{schema}}cset_members_items{{optional_suffix}}(concept_id);

CREATE INDEX csmi_idx3 ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id, concept_id);