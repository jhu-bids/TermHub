# TODO's
#  1. For each tablee: don't do anything if these tables exist & initialized
#  2. Fix syntax error. This may be a a SqlAlchemy thing only
CREATE DATABASE IF NOT EXISTS termhub_n3c;
CREATE TABLE IF NOT EXISTS code_sets (
    codeset_id INT NOT NULL PRIMARY KEY,
    concept_set_version_title VARCHAR(285),
    project VARCHAR(255),
    concept_set_name VARCHAR(255),
    source_application VARCHAR(255),
    source_application_version NUMERIC(7,3),
    created_at DATETIME,
    atlas_json TEXT,
    is_most_recent_version BOOLEAN,
    version INT,
    comments TEXT,
    intention TEXT,
    limitations TEXT,
    issues TEXT,
    update_message TEXT,
    status VARCHAR(255),
    has_review BOOLEAN,
    reviewed_by VARCHAR(255),
    created_by VARCHAR(255),
    provenance TEXT,
    atlas_json_resource_url VARCHAR(255),
    parent_version_id INT,
    authoritative_source VARCHAR(255),
    is_draft BOOLEAN
);

TRUNCATE code_sets;
LOAD DATA INFILE './termhub-csets/datasets/prepped_files/code_sets.csv'
INTO TABLE code_sets
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
# IGNORE 1 ROWS: PyCharm says syntax err & got sqlalchemy.exc.ProgrammingError: (pymysql.err.ProgrammingError) (1064, "You have an error in your SQL syntax;
# Google: mysql LOAD DATA INFILE ignore header
# https://stackoverflow.com/questions/13568707/mysql-infile-ignore-header-row
IGNORE 1 ROWS;
