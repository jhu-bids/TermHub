-- View: all_csets_view ----------------------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW {{schema}}all_csets_view{{optional_suffix}} AS (
    SELECT
        codeset_id,
        project,
        alias,
        is_most_recent_version AS mrv,
        version AS v,
        is_draft AS draft,
        archived AS arch,
        codeset_created_at::date AS ver_create,
        container_created_at::date AS cont_create,
        omop_vocab_version AS omop_voc,
        distinct_person_cnt AS perscnt,
        total_cnt AS totcnt,
        flag_cnts,
        concepts,
        container_creator,
        codeset_creator
    FROM {{schema}}all_csets);