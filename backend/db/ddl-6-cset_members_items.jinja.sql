-- Table: cset_members_items -------------------------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}cset_members_items{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}cset_members_items{{optional_suffix}} AS
SELECT
    COALESCE(csm.codeset_id, item.codeset_id) AS codeset_id,
    COALESCE(csm.concept_id, item.concept_id) AS concept_id,
    csm.codeset_id IS NOT NULL AS csm,
    item.codeset_id IS NOT NULL AS item,
    item.flags,
    array_to_string(array_remove(ARRAY[
                                     CASE WHEN item."isExcluded" THEN 'isExcluded' ELSE NULL END,
                                     CASE WHEN item."includeDescendants" THEN 'includeDescendants' ELSE NULL END,
                                     CASE WHEN item."includeMapped" THEN 'includeMapped' ELSE NULL END ],
                                 NULL), ',') AS item_flags,
    item."isExcluded",
    item."includeDescendants",
    item."includeMapped"
FROM {{schema}}concept_set_members{{optional_suffix}} csm,
FULL OUTER JOIN (
    SELECT
        codeset_id,
        concept_id,
        "isExcluded",
        "includeDescendants",
        "includeMapped",
        array_to_string(
                ARRAY[
                    CASE WHEN bool_or("includeDescendants") THEN 'D' END,
                    CASE WHEN bool_or("includeMapped") THEN 'M' END,
                    CASE WHEN bool_or("isExcluded") THEN 'X' END
                    ]::text[], ''
        ) AS flags
    FROM {{schema}}concept_set_version_item{{optional_suffix}}
    GROUP BY 1,2,3,4,5
) AS item ON csm.codeset_id = item.codeset_id
         AND csm.concept_id = item.concept_id
WHERE csm.codeset_id IS NOT NULL
   OR item.codeset_id IS NOT NULL;

CREATE INDEX {{optional_index_suffix}}csmi_idx1 ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id);

CREATE INDEX {{optional_index_suffix}}csmi_idx2 ON {{schema}}cset_members_items{{optional_suffix}}(concept_id);

CREATE INDEX {{optional_index_suffix}}csmi_idx3 ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id, concept_id);
