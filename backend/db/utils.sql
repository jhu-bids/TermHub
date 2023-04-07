
-- what i used to get table counts

set search_path = n3c;
select count(*) from code_sets;
select count(*) from concept;
select count(*) from concept_ancestor;
select count(*) from concept_relationship;
select count(*) from concept_relationship_plus;
select count(*) from concept_set_container;
select count(*) from concept_set_counts_clamped;
select count(*) from concept_set_members;
select count(*) from concept_set_version_item;
select count(*) from concepts_with_counts;
select count(*) from concepts_with_counts_ungrouped;
select count(*) from cset_members_items;
select count(*) from cset_members_items_plus;
select count(*) from deidentified_term_usage_by_domain_clamped;
select count(*) from omopconceptset;
select count(*) from omopconceptsetcontainer;
select count(*) from omopconceptsetversionitem;
select count(*) from researcher;
n3c.concept; 0
n3c.concept_ancestor; 0
n3c.concept_relationship; 0
n3c.concept_relationship_plus; 16971521
n3c.concept_set_container; 0
n3c.concept_set_counts_clamped; 0
n3c.concept_set_members; 0
n3c.concept_set_version_item; 0
n3c.concepts_with_counts; 6863475
n3c.concepts_with_counts_ungrouped; 6864315
n3c.cset_members_items; 7175324
n3c.cset_members_items_plus; 0
n3c.deidentified_term_usage_by_domain_clamped; 0
n3c.omopconceptset; 0
n3c.omopconceptsetcontainer; 0
n3c.omopconceptsetversionitem; 10000
n3c.researcher; 0



set search_path = n3c_20230221;
select count(*) from code_sets
select count(*) from concept
select count(*) from concept_ancestor
select count(*) from concept_relationship
select count(*) from concept_set_container
select count(*) from concept_set_counts_clamped
select count(*) from concept_set_members
select count(*) from concept_set_version_item
select count(*) from deidentified_term_usage_by_domain_clamped
select count(*) from omopconceptset
select count(*) from omopconceptsetcontainer
select count(*) from researcher

set search_path = n3c_before_20230206_1pm;
select count(*) from code_sets;
select count(*) from concept;
select count(*) from concept_ancestor;
select count(*) from concept_relationship;
select count(*) from concept_relationship_plus;
select count(*) from concept_set_container;
select count(*) from concept_set_counts_clamped;
select count(*) from concept_set_members;
select count(*) from concept_set_version_item;
select count(*) from concepts_with_counts;
select count(*) from concepts_with_counts_fix;
select count(*) from concepts_with_counts_ungrouped;
select count(*) from cset_members_items;
select count(*) from cset_members_items_plus;
select count(*) from deidentified_term_usage_by_domain_clamped;
select count(*) from omopconceptset;
select count(*) from omopconceptsetcontainer;
select count(*) from researcher;

n3c_before_20230206_1pm.concept; 0
n3c_before_20230206_1pm.concept_ancestor; 0
n3c_before_20230206_1pm.concept_relationship; 0
n3c_before_20230206_1pm.concept_relationship_plus; 67886084
n3c_before_20230206_1pm.concept_set_container; 0
n3c_before_20230206_1pm.concept_set_counts_clamped; 0
n3c_before_20230206_1pm.concept_set_members; 0
n3c_before_20230206_1pm.concept_set_version_item; 0
n3c_before_20230206_1pm.concepts_with_counts; 6863475
n3c_before_20230206_1pm.concepts_with_counts_fix; 6863475
n3c_before_20230206_1pm.concepts_with_counts_ungrouped; 6864321
n3c_before_20230206_1pm.cset_members_items; 8014666
n3c_before_20230206_1pm.cset_members_items_plus; 0
n3c_before_20230206_1pm.deidentified_term_usage_by_domain_clamped; 0
n3c_before_20230206_1pm.omopconceptset; 0
n3c_before_20230206_1pm.omopconceptsetcontainer; 0
n3c_before_20230206_1pm.researcher; 0


set search_path = n3c_messed_up_20230221;
select count(*) from all_csets;
select count(*) from code_sets;
select count(*) from concept;
select count(*) from concept_ancestor;
select count(*) from concept_relationship;
select count(*) from concept_relationship_plus;
select count(*) from concept_set_container;
select count(*) from concept_set_counts_clamped;
select count(*) from concept_set_json;
select count(*) from concept_set_members;
select count(*) from concept_set_version_item;
select count(*) from concepts_with_counts;
select count(*) from concepts_with_counts_ungrouped;
select count(*) from cset_members_items;
select count(*) from cset_members_items_plus;
select count(*) from deidentified_term_usage_by_domain_clamped;
select count(*) from omopconceptset;
select count(*) from omopconceptsetcontainer;
select count(*) from researcher;



n3c_messed_up_20230221.code_sets; 0
n3c_messed_up_20230221.concept; 0
n3c_messed_up_20230221.concept_ancestor; 0
n3c_messed_up_20230221.concept_relationship; 0
n3c_messed_up_20230221.concept_relationship_plus; 16971521
n3c_messed_up_20230221.concept_set_container; 0
n3c_messed_up_20230221.concept_set_counts_clamped; 0
n3c_messed_up_20230221.concept_set_json; 52
n3c_messed_up_20230221.concept_set_members; 0
n3c_messed_up_20230221.concept_set_version_item; 0
n3c_messed_up_20230221.concepts_with_counts; 6863475
n3c_messed_up_20230221.concepts_with_counts_ungrouped; 6864315
n3c_messed_up_20230221.cset_members_items; 7175324
n3c_messed_up_20230221.cset_members_items_plus; 0
n3c_messed_up_20230221.deidentified_term_usage_by_domain_clamped; 0
n3c_messed_up_20230221.omopconceptset; 0
n3c_messed_up_20230221.omopconceptsetcontainer; 0
n3c_messed_up_20230221.researcher; 0


THIS IS COMPLETE JUNK AT THE MOMENT

-- from https://github.com/Sigfried/ohdsi-api/blob/master/sql-scripts/cols-and-counts.sql
CREATE OR REPLACE
  FUNCTION :results.store_concept_id_counts(
              _schema text,
              _tbl text,
              _col text,
              _col_type text,
              target_schema text,
              target_table text
            )
  RETURNS TABLE(
                  resultsSchema text,
                  cdmSchema text,
                  table_name text,
                  column_name text,
                  column_type text,
                  count bigint
                )
  AS
  $func$
  declare sql text;
  BEGIN
    RAISE NOTICE 'getting concept_ids for %.%s', _tbl, _col;
    sql := format(
      'INSERT INTO %s.%s ' ||                       -- target_schema, target_table,
      'SELECT ' ||
      '       ''%s'' as schema, ' ||                -- _schema,
      '       ''%s'' as table_name, ' ||            -- _tbl
      '       ''%s'' as column_name, ' ||           -- _col
      '       ''%s'' as column_type, ' ||           -- _coltype
      '       %s as concept_id, ' ||                -- _col
      '       count(*) as count ' ||
      'from (select * from %s.%s ' ||               -- _schema, _tbl
      '      where %s is not null ) t ' ||          -- _col
      --'from (select * from %s.%s limit 5) t ' ||
      --'where %s > 0 ' ||
      'group by 1,2,3,4,5',
        target_schema, target_table,
        _schema,
        _tbl,
        _col,
        _col_type,
        _col,
        _schema, _tbl,
        _col
      );
    RAISE NOTICE '%', sql;
    EXECUTE sql;
  END;
  $func$ LANGUAGE plpgsql;


CREATE OR REPLACE VIEW schema_tables AS
    WITH schemas AS (
        SELECT n.nspname AS schema_name
        FROM pg_catalog.pg_namespace n
        WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
        ORDER BY 1
    ), tables AS (

    )
-- get schema names

-- get table names (on search path)
SELECT n.nspname as "Schema",
  c.relname as "Name",
  CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' WHEN 'i' THEN 'index' WHEN 'S' THEN 'sequence' WHEN 's' THEN 'special' WHEN 't' THEN 'TOAST table' WHEN 'f' THEN 'foreign table' WHEN 'p' THEN 'partitioned table' WHEN 'I' THEN 'partitioned index' END as "Type",
  pg_catalog.pg_get_userbyid(c.relowner) as "Owner"
FROM pg_catalog.pg_class c
     LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     LEFT JOIN pg_catalog.pg_am am ON am.oid = c.relam
WHERE c.relkind IN ('r','p','v','m','S','f','')
      AND n.nspname <> 'pg_catalog'
      AND n.nspname !~ '^pg_toast'
      AND n.nspname <> 'information_schema'
  AND pg_catalog.pg_table_is_visible(c.oid)
ORDER BY 1,2;
