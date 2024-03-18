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

DROP TABLE IF EXISTS public.apiruns_plus CASCADE;

WITH RankedGroups AS (
        SELECT
            *,
            substring(client from '\d+\.\d+\.\d+') AS ip3, -- sometimes fourth ip part differs for same call session
            ROW_NUMBER() OVER (PARTITION BY api_call_group_id ORDER BY timestamp::timestamp DESC) AS rn,
            EXTRACT(SECOND FROM timestamp::timestamp - (
                lag(timestamp::timestamp) OVER (PARTITION by host, substring(client from '\d+\.\d+\.\d+'), api_call_group_id ORDER BY timestamp) +
                    lag(process_seconds) OVER (PARTITION by host, substring(client from '\d+\.\d+\.\d+'), api_call_group_id ORDER BY timestamp)
                    * INTERVAL '1 second')) AS call_gap,
            CASE
              WHEN timestamp::timestamp - LAG(timestamp::timestamp) OVER
                  (PARTITION BY host, substring(client from '\d+\.\d+\.\d+'), api_call_group_id ORDER BY timestamp::timestamp) > INTERVAL '1 second' THEN 1
              ELSE 0
            END AS new_group_flag

        FROM public.api_runs
        WHERE host IN ('prod', 'dev')
          AND client NOT LIKE '216.164.48.98%'
          AND client NOT LIKE '174.99.54.40%'
          AND client NOT LIKE '136.226%' -- this one can differ by the third and fourth ip parts; just skipping it.
    ),
groups_broke_by_long_gap AS (
  SELECT *,
    host || '-' || ip3 || '-' || COALESCE(api_call_group_id::text, 'no_call_grp') || '-' ||
        SUM(new_group_flag) OVER (PARTITION BY host, ip3, api_call_group_id
            ORDER BY timestamp::timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS group_id
  FROM RankedGroups
)
SELECT * INTO public.apiruns_plus FROM groups_broke_by_long_gap;

CREATE INDEX aprpidx ON apiruns_plus (group_id );

DROP TABLE IF EXISTS public.apiruns_grouped CASCADE;

SELECT
    group_id,
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
    public.apiruns_plus
GROUP BY
    group_id /* , api_call, codeset_ids, params*/
ORDER BY group_id desc; -- group_start_time DESC, ip3

CREATE INDEX aprgidx ON apiruns_grouped(group_id);

DROP TABLE IF EXISTS public.apijoin CASCADE;

SELECT DISTINCT r.*,
                array_sort(g.api_calls) api_calls, g.duration_seconds, g.group_start_time,
                date_bin('1 week', timestamp::TIMESTAMP, TIMESTAMP '2023-10-30')::date week,
                timestamp::date date,
                FORMAT('%s of %s',
                       ROW_NUMBER() OVER(PARTITION BY r.group_id ORDER BY timestamp),
                       COUNT(*) OVER(PARTITION BY r.group_id)) AS callnum
INTO public.apijoin
FROM public.apiruns_plus r
LEFT JOIN public.apiruns_grouped g ON g.group_id = r.group_id
;

CREATE INDEX aprjidx ON public.apijoin(group_id);

/*
WITH RankedRows AS (
    SELECT host,client,api_call,result,week,codeset_ids, params, callnum, api_call_group_id,
           ROW_NUMBER() OVER(PARTITION BY column_to_partition_by ORDER BY column_to_order_by) AS rn
    FROM public.apijoin
    WHERE api_call = 'concept-ids-by-codeset-id'
    ORDER BY 9,8
)
SELECT *
FROM RankedRows
WHERE rn = 1;
--WHERE r.api_call_group_id = -1 OR g.api_call_group_id IS NULL
 */