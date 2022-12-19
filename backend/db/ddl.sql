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



/* this is all happening directly in initialize.py now:
CREATE DATABASE IF NOT EXISTS termhub_n3c;
USE termhub_n3c;
CREATE TABLE IF NOT EXISTS code_sets (
    codeset_id INT NOT NULL PRIMARY KEY,
    concept_set_version_title TEXT,
    project TEXT,
    concept_set_name TEXT,
    source_application TEXT,
    source_application_version NUMERIC(7,3),
    created_at DATETIME,
    atlas_json LONGTEXT,
    is_most_recent_version BOOLEAN,
    version INT,
    comments TEXT,
    intention TEXT,
    limitations TEXT,
    issues TEXT,
    update_message TEXT,
    status TEXT,
    has_review BOOLEAN,
    reviewed_by TEXT,
    created_by TEXT,
    provenance TEXT,
    atlas_json_resource_url TEXT,
    parent_version_id INT,
    authoritative_source TEXT,
    is_draft BOOLEAN
);
# TRUNCATE code_sets;
#
# LOAD DATA INFILE '/Users/joeflack4/projects/TermHub/termhub-csets/datasets/prepped_files/code_sets.csv'
# INTO TABLE code_sets
# FIELDS TERMINATED BY ','
# ENCLOSED BY '"'
# LINES TERMINATED BY '\n'
# IGNORE 1 ROWS;
## IGNORE 1 ROWS: PyCharm says syntax err & got sqlalchemy.exc.ProgrammingError: (pymysql.err.ProgrammingError) (1064, "You have an error in your SQL syntax
## Google: mysql LOAD DATA INFILE ignore header
## https://stackoverflow.com/questions/13568707/mysql-infile-ignore-header-row
## IGNORE 1 ROWS;
## IGNORE 1 LINES;
 */