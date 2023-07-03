-- Table: members_items_summary ----------------------------------------------------------------------------------------
DROP TABLE IF EXISTS {{schema}}members_items_summary{{optional_suffix}};

CREATE TABLE {{schema}}members_items_summary{{optional_suffix}} AS
SELECT
    codeset_id,
    CASE
        WHEN item AND csm THEN 'Expression item and member'
        WHEN item THEN 'Expression item only'
        WHEN csm THEN 'Member only'
        ELSE 'WHAT IS THIS?' END
    ||
    CASE
        WHEN item THEN ' -- '
                        ||
                        CASE WHEN LENGTH(item_flags) > 0 THEN item_flags ELSE 'no flags' END
        ELSE '' END
    AS grp,
    COUNT(*) AS cnt
FROM {{schema}}cset_members_items
GROUP by 1,2
UNION
SELECT codeset_id, 'Members' AS grp, SUM(CASE WHEN csm THEN 1 ELSE 0 END) AS cnt FROM {{schema}}cset_members_items GROUP by 1,2
UNION
SELECT codeset_id, 'Expression items' AS grp, SUM(CASE WHEN item THEN 1 ELSE 0 END) AS cnt FROM {{schema}}cset_members_items GROUP by 1,2;

CREATE INDEX mis1{{optional_index_suffix}} ON {{schema}}members_items_summary{{optional_suffix}}(codeset_id);