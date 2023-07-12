-- Indexes -------------------------------------------------------------------------------------------------------------
CREATE INDEX concept_idx{{optional_index_suffix}} ON {{schema}}concept(concept_id);

CREATE INDEX concept_idx2{{optional_index_suffix}} ON {{schema}}concept(concept_code);

CREATE INDEX csm_idx1{{optional_index_suffix}} ON {{schema}}concept_set_members(codeset_id);

CREATE INDEX csm_idx2{{optional_index_suffix}} ON {{schema}}concept_set_members(concept_id);

CREATE INDEX csm_idx3{{optional_index_suffix}} ON {{schema}}concept_set_members(codeset_id, concept_id);

CREATE INDEX vi_idx1{{optional_index_suffix}} ON {{schema}}concept_set_version_item(codeset_id);

CREATE INDEX vi_idx2{{optional_index_suffix}} ON {{schema}}concept_set_version_item(concept_id);

CREATE INDEX vi_idx3{{optional_index_suffix}} ON {{schema}}concept_set_version_item(codeset_id, concept_id);

CREATE INDEX cr_idx1{{optional_index_suffix}} ON {{schema}}concept_relationship(concept_id_1);

CREATE INDEX cr_idx2{{optional_index_suffix}} ON {{schema}}concept_relationship(concept_id_2);

CREATE INDEX cr_idx3{{optional_index_suffix}} ON {{schema}}concept_relationship(concept_id_1, concept_id_2);

CREATE INDEX ca_idx1{{optional_index_suffix}} ON {{schema}}concept_ancestor(ancestor_concept_id);

CREATE INDEX ca_idx2{{optional_index_suffix}} ON {{schema}}concept_ancestor(descendant_concept_id);

CREATE INDEX ca_idx3{{optional_index_suffix}} ON {{schema}}concept_ancestor(ancestor_concept_id, descendant_concept_id);

CREATE INDEX ca_idx4{{optional_index_suffix}} ON {{schema}}concept_ancestor(min_levels_of_separation);

CREATE INDEX cs_idx1{{optional_index_suffix}} ON {{schema}}code_sets(codeset_id);

CREATE INDEX csc_idx1{{optional_index_suffix}} ON {{schema}}concept_set_container(concept_set_id);

CREATE INDEX csc_idx2{{optional_index_suffix}} ON {{schema}}concept_set_container(concept_set_name);

CREATE INDEX csc_idx3{{optional_index_suffix}} ON {{schema}}concept_set_container(concept_set_id, created_at DESC);

CREATE INDEX cscc_idx{{optional_index_suffix}} on {{schema}}concept_set_counts_clamped(codeset_id);

CREATE INDEX term_usage_idx{{optional_index_suffix}} on {{schema}}deidentified_term_usage_by_domain_clamped(concept_id, domain);
