-- Indexes -------------------------------------------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS concept_idx on {{schema}}concept(concept_id);

CREATE INDEX IF NOT EXISTS concept_idx2 on {{schema}}concept(concept_code);

CREATE INDEX IF NOT EXISTS csm_idx1 on {{schema}}concept_set_members(codeset_id);

CREATE INDEX IF NOT EXISTS csm_idx2 on {{schema}}concept_set_members(concept_id);

CREATE INDEX IF NOT EXISTS csm_idx3 on {{schema}}concept_set_members(codeset_id, concept_id);

CREATE INDEX IF NOT EXISTS vi_idx1 on {{schema}}concept_set_version_item(codeset_id);

CREATE INDEX IF NOT EXISTS vi_idx2 on {{schema}}concept_set_version_item(concept_id);

CREATE INDEX IF NOT EXISTS vi_idx3 on {{schema}}concept_set_version_item(codeset_id, concept_id);

CREATE INDEX IF NOT EXISTS cr_idx1 on {{schema}}concept_relationship(concept_id_1);

CREATE INDEX IF NOT EXISTS cr_idx2 on {{schema}}concept_relationship(concept_id_2);

CREATE INDEX IF NOT EXISTS cr_idx3 on {{schema}}concept_relationship(concept_id_1, concept_id_2);

CREATE INDEX IF NOT EXISTS ca_idx1 on {{schema}}concept_ancestor(ancestor_concept_id);

CREATE INDEX IF NOT EXISTS ca_idx2 on {{schema}}concept_ancestor(descendant_concept_id);

CREATE INDEX IF NOT EXISTS ca_idx3 on {{schema}}concept_ancestor(ancestor_concept_id, descendant_concept_id);

CREATE INDEX IF NOT EXISTS ca_idx4 on {{schema}}concept_ancestor(min_levels_of_separation);

CREATE INDEX IF NOT EXISTS cs_idx1 on {{schema}}code_sets(codeset_id);

CREATE INDEX IF NOT EXISTS csc_idx1 on {{schema}}concept_set_container(concept_set_id);

CREATE INDEX IF NOT EXISTS csc_idx2 on {{schema}}concept_set_container(concept_set_name);

CREATE INDEX IF NOT EXISTS csc_idx3 on {{schema}}concept_set_container(concept_set_id, created_at DESC);

CREATE INDEX IF NOT EXISTS cscc_idx on {{schema}}concept_set_counts_clamped(codeset_id);

CREATE INDEX IF NOT EXISTS term_usage_idx on {{schema}}deidentified_term_usage_by_domain_clamped(concept_id, domain);
