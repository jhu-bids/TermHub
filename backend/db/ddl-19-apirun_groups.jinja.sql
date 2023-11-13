-- View: apiruns_grouped ------------------------------------------------------------------------------------
DROP TABLE IF EXISTS public.api_runs CASCADE;

CREATE TABLE IF NOT EXISTS public.api_runs (
    api_call_group_id integer,
    host text,
    client text,
    schema text not null,
    api_call text not null,
    codeset_ids integer[],
    params text,
    timestamp text not null,
    result text,
    process_seconds float
    --date text,
    --note text
);

DROP SEQUENCE IF EXISTS api_call_group_id_seq;

CREATE SEQUENCE api_call_group_id_seq START 10001;

CREATE OR REPLACE  VIEW public.apiruns_grouped AS (
WITH RankedGroups AS (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY api_call_group_id ORDER BY timestamp::timestamp DESC) AS rn
        FROM
            public.api_runs
    )
SELECT
    host,
    client,
    schema,
    api_call_group_id,
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
    api_call_group_id, host, client, schema /* , api_call, codeset_ids, params*/
ORDER BY api_call_group_id desc -- group_start_time DESC, client
);