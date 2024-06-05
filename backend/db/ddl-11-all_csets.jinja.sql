-- Table: all_csets ----------------------------------------------------------------------------------------------------
-- todo: change CREATE TABLE cset_term_usage_rec_counts to `CREATE TEMP TABLE`?
DROP TABLE IF EXISTS {{schema}}all_csets{{optional_suffix}} CASCADE;

DROP TABLE IF EXISTS {{schema}}cset_term_usage_rec_counts;
CREATE TABLE {{schema}}cset_term_usage_rec_counts AS
    SELECT csm.codeset_id, SUM(cwc.total_cnt) AS total_cnt
    FROM {{schema}}concept_set_members csm
    JOIN {{schema}}concepts_with_counts cwc ON csm.concept_id = cwc.concept_id
    WHERE cwc.total_cnt > 0
    GROUP BY csm.codeset_id;

CREATE INDEX ctu_idx1{{optional_index_suffix}} ON {{schema}}cset_term_usage_rec_counts(codeset_id);

CREATE TABLE {{schema}}all_csets{{optional_suffix}} AS
-- table instead of view for performance (no materialized views in mySQL)
-- TODO: but now we're on postgres should it be a materialized view?
WITH ac AS (SELECT DISTINCT cs.codeset_id,
                            cs.concept_set_version_title,
                            cs.project,
                            cs.concept_set_name,
                            csc.alias,
                            cs.source_application,
                            cs.source_application_version,
                            cs.created_at                                  AS codeset_created_at,
                            cs.atlas_json,
                            cs.is_most_recent_version,
                            cs.version,
                            cs.comments,
                            cs.intention                                   AS codeset_intention,
                            cs.limitations,
                            cs.issues,
                            cs.update_message,
                            cs.status                                      AS codeset_status,
                            cs.has_review,
                            cs.reviewed_by,
                            cs.created_by                                  AS codeset_created_by,
                            cs.provenance,
                            cs.atlas_json_resource_url,
                            cs.parent_version_id,
                            cs.authoritative_source,
                            cs.is_draft,
                            ocs.rid                                        AS codeset_rid,
                            csc.project_id,
                            csc.assigned_informatician,
                            csc.assigned_sme,
                            csc.status                                     AS container_status,
                            csc.stage,
                            csc.intention                                  AS container_intention,
                            csc.n3c_reviewer,
                            csc.archived,
                            csc.created_by                                 AS container_created_by,
                            csc.created_at                                 AS container_created_at,
                            cs.omop_vocab_version,
                            ocsc.rid                                       AS container_rid,
                            -- COALESCE(members.concepts, 0) AS members,
                            -- COALESCE(items.concepts, 0) AS items,
                            COALESCE(cscc.approx_distinct_person_count, 0) AS distinct_person_cnt,
                            COALESCE(cscc.approx_total_record_count, 0)    AS total_cnt,
                            COALESCE(ctu.total_cnt, 0)                     AS total_cnt_from_term_usage
            FROM {{schema}}code_sets cs
                     LEFT JOIN {{schema}}OMOPConceptSet ocs
            ON cs.codeset_id = ocs."codesetId" -- need quotes because of caps in colname
                JOIN {{schema}}concept_set_container csc ON cs.concept_set_name = csc.concept_set_name
                LEFT JOIN {{schema}}omopconceptsetcontainer ocsc ON csc.concept_set_id = ocsc."conceptSetId"
                LEFT JOIN {{schema}}concept_set_counts_clamped cscc ON cs.codeset_id = cscc.codeset_id
                LEFT JOIN {{schema}}cset_term_usage_rec_counts ctu ON cs.codeset_id = ctu.codeset_id
/*
 want to add term usage record counts, tried this code:
     COALESCE(cwc.total_cnt, 0)                     AS total_cnt_from_term_usage
     ...
    LEFT JOIN concept_set_members csm ON cs.codeset_id = csm.codeset_id
    LEFT JOIN concepts_with_counts cwc ON csm.concept_id = cwc.concept_id
 but it makes things way too slow. should try pre-generating a table with
     with just codeset_id and total_term_usage_record_cnt, and join that
 */
            )
SELECT ac.*,
       cscnt.counts,
       cscnt.flag_cnts,
       CAST(cscnt.counts->>'Members' as int) as concepts,
       rcon.name AS container_creator,
       rver.name AS codeset_creator
FROM ac
LEFT JOIN {{schema}}codeset_counts cscnt ON ac.codeset_id = cscnt.codeset_id
LEFT JOIN {{schema}}researcher rcon ON ac.container_created_by = rcon."multipassId"
LEFT JOIN {{schema}}researcher rver ON ac.codeset_created_by = rver."multipassId" ;

CREATE INDEX ac_idx1{{optional_index_suffix}} ON {{schema}}all_csets{{optional_suffix}}(codeset_id);

CREATE INDEX ac_idx2{{optional_index_suffix}} ON {{schema}}all_csets{{optional_suffix}}(concept_set_name);

DROP TABLE {{schema}}cset_term_usage_rec_counts;