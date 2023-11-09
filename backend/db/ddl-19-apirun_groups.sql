-- Table: concept_ancestor_plus ------------------------------------------------------------------------------------
DROP TABLE IF EXISTS public.apiruns_grouped CASCADE;

CREATE TABLE IF NOT EXISTS public.apiruns_grouped AS (
WITH OrderedRuns AS (
    SELECT
        *,
        LAG(timestamp::timestamp) OVER (PARTITION BY client ORDER BY timestamp::timestamp) as previous_timestamp,
        LAG(client) OVER (ORDER BY timestamp::timestamp) as previous_client
    FROM
        public.api_runs
),
GroupFlags AS (
    SELECT
        *,
        CASE
            WHEN previous_client IS DISTINCT FROM client OR
                 previous_timestamp IS NULL OR
                 timestamp::timestamp - previous_timestamp > INTERVAL '1 minutes'
            THEN 1
            ELSE 0
        END as new_group_flag
    FROM
        OrderedRuns
),
GroupNumbers AS (
    SELECT
        *,
        SUM(new_group_flag) OVER (ORDER BY client, timestamp::timestamp) AS group_number
    FROM
        GroupFlags
),
RankedGroups AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY group_number ORDER BY timestamp::timestamp DESC) AS rn
    FROM
        GroupNumbers
)
SELECT
    host,
    client,
    schema,
    group_number,
    /*
    codeset_ids,
    params,
    */
    ARRAY_AGG(api_call) AS api_calls,
    MIN(timestamp::timestamp) as group_start_time,
    MAX(timestamp::timestamp) as group_end_time,
    (MAX(timestamp::timestamp) - MIN(timestamp::timestamp)) +
    CASE WHEN MAX(rn) = 1 THEN MAX(process_seconds) * INTERVAL '1 second' ELSE INTERVAL '0 seconds' END as duration_seconds
FROM
    RankedGroups
GROUP BY
    group_number, host, client, schema, group_number /* , api_call, codeset_ids, params*/
ORDER BY
    group_start_time DESC, client
);