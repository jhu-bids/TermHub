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

CREATE INDEX apridx ON api_runs (api_call_group_id );

DROP SEQUENCE IF EXISTS public.api_call_group_id_seq;

CREATE SEQUENCE public.api_call_group_id_seq START 10001;

DROP TABLE IF EXISTS public.apiruns_grouped CASCADE;

WITH RankedGroups AS (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY api_call_group_id ORDER BY timestamp::timestamp DESC) AS rn
        FROM public.api_runs
        WHERE api_call_group_id IS NOT NULL
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
INTO public.apiruns_grouped
FROM
    RankedGroups
GROUP BY
    api_call_group_id, host, client, schema /* , api_call, codeset_ids, params*/
ORDER BY api_call_group_id desc; -- group_start_time DESC, client

CREATE INDEX aprgidx ON apiruns_grouped(api_call_group_id);

DROP TABLE IF EXISTS public.apijoin CASCADE;

SELECT DISTINCT r.*, array_sort(g.api_calls) api_calls, g.duration_seconds, g.group_start_time,
                date_bin('1 week', timestamp::TIMESTAMP, TIMESTAMP '2023-10-30')::date week,
                timestamp::date date
INTO public.apijoin
FROM public.api_runs r
LEFT JOIN public.apiruns_grouped g ON g.api_call_group_id = r.api_call_group_id AND g.api_call_group_id != -1
;

CREATE INDEX aprjidx ON public.apijoin(api_call_group_id);

--WHERE r.api_call_group_id = -1 OR g.api_call_group_id IS NULL