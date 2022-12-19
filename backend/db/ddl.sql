/* TODO's
    1. For each table: don't do anything if these tables exist & initialized
    2. Add alters to fix data types
    3. Run stuff in this file again (not doing that currently)
*/

CREATE INDEX IF NOT EXISTS concept_idx ON concept(concept_id);

CREATE INDEX IF NOT EXISTS concept_idx2 ON concept(concept_code);

CREATE INDEX IF NOT EXISTS csm_idx1 ON concept_set_members(codeset_id);

CREATE INDEX IF NOT EXISTS csm_idx2 ON concept_set_members(concept_id);

CREATE INDEX IF NOT EXISTS csm_idx3 ON concept_set_members(codeset_id, concept_id);

CREATE INDEX IF NOT EXISTS vi_idx1 ON concept_set_version_item(codeset_id);

CREATE INDEX IF NOT EXISTS vi_idx2 ON concept_set_version_item(concept_id);

CREATE INDEX IF NOT EXISTS vi_idx3 ON concept_set_version_item(codeset_id, concept_id);

CREATE INDEX IF NOT EXISTS cr_idx1 ON concept_relationship(concept_id_1);

CREATE INDEX IF NOT EXISTS cr_idx2 ON concept_relationship(concept_id_2);

CREATE INDEX IF NOT EXISTS cr_idx3 ON concept_relationship(concept_id_1, concept_id_2);

CREATE INDEX IF NOT EXISTS cs_idx1 ON code_sets(codeset_id);

CREATE INDEX IF NOT EXISTS csc_idx1 ON concept_set_container(concept_set_id);

CREATE INDEX IF NOT EXISTS csc_idx2 ON concept_set_container(concept_set_name);

CREATE INDEX IF NOT EXISTS csc_idx3 ON concept_set_container(concept_set_id, created_at DESC);

DROP TABLE IF EXISTS all_csets;

CREATE TABLE all_csets AS           -- table instead of view for performance
                                    -- (no materialized views in mySQL)
SELECT DISTINCT
		cs.codeset_id,
		cs.concept_set_version_title,
		cs.project,
		cs.concept_set_name,
		cs.source_application,
		cs.source_application_version,
		cs.created_at AS codeset_created_at,
		cs.atlas_json,
		cs.is_most_recent_version,
		cs.version,
		cs.comments,
		cs.intention AS codeset_intention,
		cs.limitations,
		cs.issues,
		cs.update_message,
		cs.status AS codeset_status,
		cs.has_review,
		cs.reviewed_by,
		cs.created_by AS codeset_created_by,
		cs.provenance,
		cs.atlas_json_resource_url,
		cs.parent_version_id,
		cs.authoritative_source,
		cs.is_draft,
        ocs.rid AS codeset_rid,
		csc.project_id,
        csc.assigned_informatician,
        csc.assigned_sme,
        csc.status AS container_status,
        csc.stage,
        csc.intention AS container_intention,
        csc.n3c_reviewer,
        csc.alias,
        csc.archived,
        csc.created_by AS container_created_by,
        csc.created_at AS container_created_at,
        ocsc.rid AS container_rid,
		COALESCE(cids.concepts, 0) AS concepts,
        cscc.approx_distinct_person_count,
        cscc.approx_total_record_count
FROM code_sets cs
LEFT JOIN OMOPConceptSet ocs ON cs.codeset_id = ocs."codesetId" -- need quotes because of caps in colname
JOIN concept_set_container csc ON cs.concept_set_name = csc.concept_set_name
LEFT JOIN omopconceptsetcontainer ocsc ON csc.concept_set_id = ocsc."conceptSetId"
LEFT JOIN (
	SELECT codeset_id, COUNT(DISTINCT concept_id) concepts
	FROM concept_set_members
    GROUP BY codeset_id
) cids ON cs.codeset_id = cids.codeset_id
LEFT JOIN concept_set_counts_clamped cscc ON cs.codeset_id = cscc.codeset_id;

CREATE INDEX  ac_idx1 ON all_csets(codeset_id);

CREATE INDEX  ac_idx2 ON all_csets(concept_set_name);

DROP TABLE IF EXISTS cset_members_items;

CREATE TABLE cset_members_items AS
SELECT
        COALESCE(csm.codeset_id, item.codeset_id) AS codeset_id,
        COALESCE(csm.concept_id, item.concept_id) AS concept_id,
        csm.codeset_id IS NOT NULL AS csm,
        item.codeset_id IS NOT NULL AS item,
        array_to_string(array_remove(ARRAY[
              CASE WHEN item."isExcluded" THEN 'isExcluded' ELSE NULL END,
              CASE WHEN item."includeDescendants" THEN 'includeDescendants' ELSE NULL END,
              CASE WHEN item."includeMapped" THEN 'includeMapped' ELSE NULL END ],
            NULL), ',') AS item_flags
FROM concept_set_members csm
FULL OUTER JOIN concept_set_version_item item
   ON csm.codeset_id = item.codeset_id
  AND csm.concept_id = item.concept_id
WHERE csm.codeset_id IS NOT NULL
   OR item.codeset_id IS NOT NULL;


-- concept_set_container has duplicate records except for the created_at col
--  get rid of duplicates, keeping the most recent.
--  code from https://stackoverflow.com/a/28085614/1368860
--      which also has code that works for databases other than postgres, if we ever need that

WITH deduped AS (
    SELECT DISTINCT ON (concept_set_id) concept_set_id, created_at
    FROM concept_set_container
    ORDER BY concept_set_id, created_at DESC
)
DELETE FROM concept_set_container csc
WHERE  NOT EXISTS (
   SELECT FROM deduped dd
   WHERE csc.concept_set_id = dd.concept_set_id
     AND csc.created_at = dd.created_at
);


