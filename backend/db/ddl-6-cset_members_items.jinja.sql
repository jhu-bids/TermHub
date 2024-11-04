-- Table: cset_members_items -------------------------------------------------------------------------------------------
-- Doesn't have {{optional_suffix}} for _old and _new because this is a core table and won't be re-created during refreshes.
CREATE TEMP TABLE csvi AS   /* there are lots of copies of the same concept_set_version_item records with different
                               item_ids for some reason */
SELECT DISTINCT
   csv.codeset_id,
   csv.concept_id,
   csv."isExcluded",
   csv."includeDescendants",
   csv."includeMapped"
   -- csv.annotation, /* these can create duplicates, but there are others (not many, but enough to mess things up */
   -- csv.source_application
FROM {{schema}}concept_set_version_item csv;

CREATE TEMP TABLE csmi1 AS
SELECT DISTINCT
    csvi.codeset_id,
    csvi.concept_id,
    csm.concept_id IS NOT NULL AS "csm",
    true AS "item",
    concat_ws('',
        CASE WHEN "includeDescendants" THEN 'D' ELSE '' END,
        CASE WHEN "includeMapped" THEN 'M' ELSE '' END,
        CASE WHEN "isExcluded" THEN 'X' ELSE '' END
    ) AS flags,
    "isExcluded",
    "includeDescendants",
    "includeMapped"
FROM csvi
LEFT JOIN {{schema}}concept_set_members csm ON csvi.codeset_id = csm.codeset_id AND csvi.concept_id = csm.concept_id;

DROP TABLE csvi;

CREATE TEMP TABLE csmi2 AS
SELECT DISTINCT
    csm.codeset_id,
    csm.concept_id,
    true AS "csm",
    false AS "item",
    NULL::text AS flags,
    NULL::bool AS "isExcluded",
    NULL::bool AS "includeDescendants",
    NULL::bool AS "includeMapped"
FROM {{schema}}concept_set_members csm
LEFT JOIN csmi1 ON csm.codeset_id = csmi1.codeset_id AND csm.concept_id = csmi1.concept_id
WHERE csmi1.concept_id IS NULL
UNION
SELECT * FROM csmi1;

DROP TABLE csmi1;

DROP TABLE IF EXISTS {{schema}}cset_members_items{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}cset_members_items{{optional_suffix}} AS
SELECT
    csmi2.*,
    c.vocabulary_id,
    c.standard_concept,
    c.concept_code,
    c.concept_name,
    c.concept_class_id
FROM {{schema}}code_sets cs
LEFT JOIN csmi2 ON cs.codeset_id = csmi2.codeset_id
JOIN {{schema}}concept c ON csmi2.concept_id = c.concept_id
WHERE csmi2.codeset_id IS NOT NULL;

DROP TABLE csmi2;

CREATE INDEX csmi_idx1{{optional_index_suffix}} ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id);

CREATE INDEX csmi_idx2{{optional_index_suffix}} ON {{schema}}cset_members_items{{optional_suffix}}(concept_id);

CREATE INDEX csmi_idx3{{optional_index_suffix}} ON {{schema}}cset_members_items{{optional_suffix}}(codeset_id, concept_id);
