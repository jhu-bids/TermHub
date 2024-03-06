DROP TABLE IF EXISTS {{schema}}concept_set_json{{optional_suffix}} CASCADE;

CREATE TABLE IF NOT EXISTS {{schema}}concept_set_json{{optional_suffix}} (
    codeset_id integer,
    json_data json
);

CREATE INDEX csj{{optional_index_suffix}} ON {{schema}}concept_set_json{{optional_suffix}}(source_id);