
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
