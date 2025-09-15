-- Table: codeset_counts -----------------------------------------------------------------------------------------------
-- For each codeset, create JSON structures that aggregate the count of each type of member, e.g. "expression item only"
-- , "member only", and "Expression item and member", and also the number of members that have membership due to
-- associated flag, e.g. "M" because they are mapped, or D because they are descendants.
DROP TABLE IF EXISTS {{schema}}codeset_counts{{optional_suffix}} CASCADE;

CREATE TABLE {{schema}}codeset_counts{{optional_suffix}} AS
WITH m1 AS (
  SELECT m1.codeset_id, json_object_agg(m1.grp, m1.cnt) AS counts
  FROM {{schema}}members_items_summary m1
  GROUP BY codeset_id
), m2 AS (
    SELECT codeset_id, json_object_agg(flags, cnt) AS flag_cnts
    FROM (
        SELECT codeset_id, flags, cnt
        FROM {{schema}}members_items_summary
        WHERE length(flags) > 0
        /*      do we care about the items with no flags?
        UNION
        SELECT codeset_id, 'No flags' AS flags, SUM(cnt) AS cnt
        FROM {{schema}}members_items_summary
        WHERE grp LIKE '%no flags'
        GROUP BY codeset_id
         */
    ) nf
    GROUP BY codeset_id
)
SELECT m1.*, m2.flag_cnts
FROM m1
LEFT JOIN m2 ON m1.codeset_id = m2.codeset_id;

CREATE INDEX csc1{{optional_index_suffix}} ON {{schema}}codeset_counts{{optional_suffix}}(codeset_id);