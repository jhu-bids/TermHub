# TODO's
#  1. For each table: don't do anything if these tables exist & initialized
#  2. Fix syntax error. This may be a a SqlAlchemy thing only
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

# IGNORE 1 ROWS: PyCharm says syntax err & got sqlalchemy.exc.ProgrammingError: (pymysql.err.ProgrammingError) (1064, "You have an error in your SQL syntax
# Google: mysql LOAD DATA INFILE ignore header
# https://stackoverflow.com/questions/13568707/mysql-infile-ignore-header-row
# IGNORE 1 ROWS;
# IGNORE 1 LINES;
