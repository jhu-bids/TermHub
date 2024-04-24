"""AMIA paper 2024: Statistics

todo's (minor)
 - get_dataset_with_mods(): Messy to have fetching of dataset and also modification in 1 function. This adds client IP.

Resources
- GH issue: https://github.com/jhu-bids/TermHub/issues/631
- Paper: https://livejohnshopkins-my.sharepoint.com/:w:/g/personal/sgold15_jh_edu/EXbuxwBsb0pPgFfgPYjR6qgBlJ1gmpqsMPYJ3vn6Y_HnYw?e=4%3ApEDbMe&fromShare=true&at=9&CID=d4663c40-1ebe-db59-8cf5-2bc091d45692

Other queries:
- Value set Size
with c as (select count(*) cnt from cset_members_items group by codeset_id)
select 10^round(log10(cnt)) || ' - ' || 10 * 10^round(log10(cnt)) - 1 value_set_size, count(*) value_sets
from c group by 1 order by 1 desc;
┌─────────────────┬────────────┐
│ value_set_size  │ value_sets │
├─────────────────┼────────────┤
│ 1 - 9           │        774 │
│ 10 - 99         │       1862 │
│ 100 - 999       │       2596 │
│ 1000 - 9999     │       1357 │
│ 10000 - 99999   │        537 │
│ 100000 - 999999 │         64 │
└─────────────────┴────────────┘

- IDK what this one is
SELECT host,client,result, replace(result, ' rows', '') concept_ids, week,group_id
FROM public.apijoin
WHERE api_call = 'codeset-ids-by-concept-id'
"""
import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Dict, List, Union

import numpy as np
import pandas as pd
from sqlalchemy import RowMapping

from backend.db.utils import get_db_connection, sql_query

THIS_DIR = Path(os.path.dirname(__file__))
PROJECT_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from backend.routes.db import usage_query


INDIR = THIS_DIR / 'input'
OUTDIR = THIS_DIR / 'output'
USAGE_JOINED_CSV_PATH = INDIR / 'api_runs_w_groups_filtered.csv'
USAGE_UNJOINED_CSV_PATH = INDIR / 'api_runs.csv'
OUT_CSV_PATH_ALL = OUTDIR / 'summary.csv'
OUT_CSV_DEV_UNFILTERED_PATH = OUTDIR / 'summary_dev_unfiltered.csv'
OUT_CSV_DEV_FILTERED_PATH = OUTDIR / 'summary_dev_filtered.csv'


def setup():
    """Setup any environmental prerequisites"""
    # handles like:
    # SettingWithCopyWarning:
    # A value is trying to be set on a copy of a slice from a DataFrame.
    # Try using .loc[row_indexer,col_indexer] = value instead
    # See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
    #   df_get_csets['codeset_ids'] = df_get_csets['codeset_ids'].astype(str)
    pd.options.mode.chained_assignment = None  # default='warn'

    if not INDIR.exists():
        INDIR.mkdir()
    if not OUTDIR.exists():
        OUTDIR.mkdir()


def filename_format(filename: str) -> str:
    """Format filename"""
    return filename.replace(' ', '_').lower().replace('(', '').replace(')', '')\
        .replace(',', '').replace(' / ', ' ').replace('/', '').replace('  ', ' ')


def api_runs_query(verbose=False):
    """Get all records from api_runs table"""
    t0 = datetime.now()
    with get_db_connection() as con:
        data: List[RowMapping] = sql_query(
            con, """SELECT * FROM public.apiruns_plus""")
                # SELECT DISTINCT *,
                # date_bin('1 week', timestamp::TIMESTAMP, TIMESTAMP '2023-10-30')::date week,
                # timestamp::date date FROM public.api_runs r""")
    data: List[Dict] = [dict(d) for d in data]
    if verbose:
        print(f'api_runs_query(): Fetched {len(data)} records in n seconds: {(datetime.now() - t0).seconds}')
    return data


def histogram_query_concepts_in_calls(filter_nulls=True) -> pd.DataFrame:
    """Concepts in calls

    result, modified (NULLs removed, at the very least)
    ┌─────────────────────┬───────┐
    │  concepts_in_call   │ calls │
    ├─────────────────────┼───────┤
    │ 1 - 9               │    20 │
    │ 10 - 99             │  1,642 │
    │ 100 - 999           │   855 │
    │ 1000 - 9999         │   505 │
    │ 10000 - 99999       │   153 │
    │ 100000 - 999999     │   121 │
    │ 1000000 - 9999999   │     3 │
    │ 10000000 - 99999999 │     2 │
    └─────────────────────┴───────┘
    """
    # Query
    qry = """
        WITH c1 AS (
          SELECT replace(result, ' rows', '') cnt FROM public.apijoin
          WHERE api_call IN ('codeset-ids-by-concept-id', 'concept', 'get-cset-members-items')
        ), c2 AS (
          SELECT CASE WHEN cnt ~ '^[0-9]+$' THEN cnt::integer END AS cnt FROM c1
        )
        SELECT 10^round(log10(cnt)) || ' - ' || 10 * 10^round(log10(cnt)) - 1 concepts_in_call, count(*) calls
        FROM c2 GROUP BY 1 ORDER BY 1 DESC;"""
    with get_db_connection() as con:
        data: List[RowMapping] = sql_query(con, qry)
    data: List[Dict] = [dict(d) for d in data]
    df = pd.DataFrame(data)
    # Filter
    if filter_nulls:
        df = df[df['concepts_in_call'].notna()]
    # Format
    def relabel(val):
        """Relabel column vals: log10"""
        min_val = val.split(' - ')[0]
        n = min_val.count('0')
        return f'10^{n}-10^{n+1}'
    df['concepts_in_call'] = df['concepts_in_call'].apply(relabel)
    return df


# todo: y axis also in log scale
def plot_concepts_in_calls(log_scale=True):
    """Plot concepts in calls"""
    # Vars
    df: pd.DataFrame = histogram_query_concepts_in_calls()
    xdata = df['concepts_in_call'].tolist()
    ydata = df['calls']
    title = f'n concepts in API calls{" (log scale)" if log_scale else ""}'
    xlab = 'Concepts in call'
    ylab = 'Number of calls'
    filename = filename_format(title)

    # Big
    plt.figure(figsize=(10, 6))
    # plt.bar(xdata, ydata, color='skyblue', log=log_scale)  # same
    plt.bar(xdata, ydata, log=log_scale)  # same
    plt.xlabel(xlab)
    plt.ylabel(ylab)
    plt.title(title)  # same
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTDIR / f'{filename}.png', dpi=500)
    plt.clf()

    # Small
    # noinspection DuplicatedCode todo
    plt.figure(figsize=(3, 1))
    # plt.bar(xdata, ydata, color='skyblue', log=log_scale)  # same
    plt.bar(xdata, ydata, log=log_scale)  # same
    plt.title(title)  # same
    plt.rcParams["font.size"] = "5"
    plt.tick_params(axis='y', which='both', left=False, labelleft=False)  # Turn off y-axis ticks and labels
    plt.xticks(rotation=90)
    plt.savefig(OUTDIR / f'{filename} - small.png', bbox_inches='tight', dpi=100)
    plt.clf()

    # Small 2
    # - same except no rotation and diff xdata
    xdata = ['<' + x.split('-')[1] for x in xdata]
    # noinspection DuplicatedCode todo
    plt.figure(figsize=(3, 1))
    # plt.bar(xdata, ydata, color='skyblue', log=log_scale)  # same
    plt.bar(xdata, ydata, log=log_scale)  # same
    plt.title(title)  # same
    plt.rcParams["font.size"] = "5"
    plt.tick_params(axis='y', which='both', left=False, labelleft=False)  # Turn off y-axis ticks and labels
    # plt.xticks(rotation=90)
    plt.savefig(OUTDIR / f'{filename} - small2.png', bbox_inches='tight', dpi=100)
    plt.clf()


def get_concept_counts(row: pd.Series) -> int:
    """Get concept counts"""
    null_token = 0  # I'd rather return NULL but for expedition, sticking w/ this for now
    if row['api_call'] not in ('codeset-ids-by-concept-id', 'concept', 'get-cset-members-items'):
        return null_token
    x = row['result']
    return int(x.split(' ')[0]) if x and x.endswith(' rows') else null_token


def get_dataset_with_mods(func: Callable, path: Union[str, Path], use_cache=False, verbose=True) -> pd.DataFrame:
    """Get data to be analyzed: JOIN of api_runs and apiruns_grouped

    Mods: Adds client IP column. Filters out null call groups."""
    if not use_cache:
        data: List[Dict] = func(verbose)
        df = pd.DataFrame(data)
    else:
        # Fetch data
        if not os.path.exists(path):
            # Fetch
            data: List[Dict] = func(verbose)
            df = pd.DataFrame(data)
            # Save
            t0 = datetime.now()
            df.to_csv(path, index=False)
            if verbose:
                print(f'Wrote {len(df)} records to {path} in n seconds: {(datetime.now() - t0).seconds}')
        else:
            # Read
            t0 = datetime.now()
            df = pd.read_csv(path)
            if verbose:
                print(f'Read {len(df)} records from {path} in n seconds: {(datetime.now() - t0).seconds}')
    # Mods
    # - client ip
    df['client_ip'] = df['client'].apply(lambda x: x.split(':')[0])
    # - duration_seconds_float && session duration / concept count
    if 'duration_seconds' in df.columns:
        # - duration_seconds_float
        df['duration_seconds_float'] = df['duration_seconds'].apply(lambda x: x.total_seconds())
        # - session duration / concept count
        df['cnt'] = df.apply(get_concept_counts, axis=1)
        df['cnt_tot'] = df.groupby('group_id')['cnt'].transform('sum')
        df['duration_sec_per_concept'] = df['duration_seconds_float'] / df['cnt_tot']
        # duration_sec_per_1k_concepts: didn't prove useful. visually the same anyway
        # df['duration_sec_per_1k_concepts'] = df['duration_seconds_float'] / (df['cnt_tot'] / 1000)

    # Filtering
    df = preprocess_null_call_groups(df, verbose) # shouldn't do anything
    # Formatting
    df = df.fillna('')  # fixes problem w/ .str.contains() ops
    return df


def filter_dev_data(df: pd.DataFrame, verbose=True) -> pd.DataFrame:
    """Preprocess data: remove developers"""
    # Devs accessing dev/prod
    developer_ips = {'Singgie': '216.164.48.98', 'Joe': '174.99.54.40'}
    if verbose:
        print('Filtered out n records based on IP addresses of each developer accesing dev/prod:')
        for dev, ip in developer_ips.items():
            df_i = df[df['client_ip'] == ip]
            print(f'  - {dev}: {len(df_i)}')
    df2 = df[~df['client_ip'].isin(list(developer_ips.values()))]
    # Devs running locally
    count_before = len(df2)
    df2 = df2[df2['host'].isi(['dev', 'prod'])]
    if verbose:
        print('Filtered out n records based devs running locally: ',  count_before - len(df2))
    # Test cases being run by GitHub actions: IPs unknown
    test_cases = [
        '[1000002363, 1000002657, 1000007602, 1000013397, 1000010688, 1000015307, 1000031299]',  # many small
        '[1000002363]'  # single small
    ]
    sessions = set()
    len_before = len(df2)
    df2['codeset_ids_str'] = df2['codeset_ids'].astype(str)
    for case in test_cases:
        df_i = df2[(df2['api_call'] == 'get-csets') & (df2['codeset_ids_str'] == case)]
        sessions.update(set(df_i['group_id']))
    # -1 is an erroneous api_call_group_id linked to otherwise contextually valid records
    if float(-1) in sessions:
        sessions.remove(float(-1))
    df2 = df2[~df2['group_id'].isin(sessions)]
    if verbose:
        print(f'Filtered out n records created by test cases: ', len_before - len(df2))
    return df2

def preprocess_null_call_groups(df: pd.DataFrame, verbose=True) -> pd.DataFrame:
    """Preprocess data: remove null api_call_group_id

    These are cases from before we added this feature, or where we called the backend directly.

    As of 2024/03/14 this doesn't have an effect. No NULL groups."""
    df2 = df[~df['group_id'].isna()]
    if verbose:
        print(f'Filtered out n records based on null group_id: ', len(df) - len(df2))
    return df2


# TODO: utilize df_apiruns
def summary_stats(
    df_apiruns: pd.DataFrame, df_w_groups_filtered: pd.DataFrame, outpath: Union[str, Path] = None
):
    """Generate summary statistics for given datasets

    :param df_apiruns: Includes full logs, even for groups that have erroneous -1 as the api_call_group_id. This is only
     used for tallying unique IP addresses.
    :param df_w_groups_filtered: This is a JOIN of apiruns and apiruns_grouped tables, with erroneous api_call_group_id
     of -1 filtered out."""
    # Get summary statistics
    summary = {}
    summary['Total log records'] = len(df_apiruns)
    summary['IP addresses'] = len(df_apiruns['client_ip'].unique())
    summary['Log records -- developer IPs removed'] = len(df_w_groups_filtered)
    summary['Log sessions'] = len(df_w_groups_filtered['group_id'].unique())
    summary['Sessions with errors'] = df_w_groups_filtered[df_w_groups_filtered['result'].str.lower().str.contains('error')][
        'group_id'].nunique()
    summary['Developer API call errors'] = len(df_apiruns[df_apiruns['result'].str.lower().str.contains('error')])
    summary['User API call errors'] = (summary['Developer API call errors'] -
                                       len(df_w_groups_filtered[df_w_groups_filtered['result']
                                           .str.lower().str.contains('error')]))

    # Value set combos
    df_get_csets = df_w_groups_filtered[df_w_groups_filtered['api_call'] == 'get-csets']
    # summary['Value set combos'] = len(set([tuple(x) for x in df_get_csets['codeset_ids']]))

    # todo: temp: analysis
    #  - analyze uniqueness of get-csets calls within an API call group session
    # diff_get_csets_vs_groups=35; i feel like this should be equal to some calc involving next 4 vars, but not sure
    # noinspection PyUnusedLocal
    diff_get_csets_vs_groups = len(df_get_csets) - len(df_get_csets['group_id'].unique())  # 35
    diff_codeset_ids_in_group__n_instances = 0  # 1
    diff_codeset_ids_in_group__n_calls = 0  # 2
    mult_get_cset_in_session__n_instances = 0  # 30
    mult_get_cset_in_session__n_calls = 0  # 64
    # todo: maybe convert to str in pre-processing instead, if need 'str' more than temporarily
    df_get_csets['codeset_ids'] = df_get_csets['codeset_ids'].astype(str)
    for group_id, group_data in df_get_csets.groupby('group_id'):
        if len(group_data) > 1 and len(group_data['codeset_ids'].unique()) > 1:
            diff_codeset_ids_in_group__n_instances += 1
            diff_codeset_ids_in_group__n_calls += len(group_data)
        elif len(group_data) > 1:
            mult_get_cset_in_session__n_instances += 1
            mult_get_cset_in_session__n_calls += len(group_data)

    df = pd.DataFrame([{'Measure': k, 'Value': v} for k, v in summary.items()])
    if outpath:
        df.to_csv(outpath, index=False)
    return df


def plot_render(
    data: List[Union[float, int]] , title: str, xlab: str, ylab: str, bins = None, small=False, is_timeseries=False,
    log_scale=False, xtick_fix=False, xtick_step=None
):
    """Close out plot

    :param: tick_fix: Turned off by default because increases overall exec time from 5 to 28 seconds"""
    title = title + f'{" (log scale)" if log_scale else ""}'
    # Initialize plot
    if small:
        plt.figure(figsize=(3, 1))  # fig = plt.figure(figsize=(1, 0.5))
    if bins:
        plt.hist(data, bins=bins, edgecolor='black', alpha=0.7, log=log_scale)
    else:
        plt.hist(data, edgecolor='black', alpha=0.7, log=log_scale)
    # Name
    filename = filename_format(title)
    # Title
    # Valid font size are xx-small, x-small, small, medium, large, x-large, xx-large, larger, smaller, None
    # plt.title(title, fontsize='x-small' if small else 'medium')  # medium is the default
    plt.title(title)
    plt.grid(True)
    # X Ticks: center of bars rather than to the left
    # todo: why ticks & labels getting super bolded with this fix?
    if not is_timeseries and xtick_fix:
        plt.xticks([edge + 0.5 for edge in data[:-1]], data[:-1])
    if xtick_step:
        plt.xticks(range(0, int(max(data)), xtick_step), rotation=45)

    if small:
        # Font size
        # todo: this isn't working; not a big priority
        plt.rcParams["font.size"] = "6" if len(title) < 30 else "6"  # long titles make plot smaller
        # Axis
        if not is_timeseries:  # it makes sense to get rid of axis for timeseries, but not otherwise
            plt.tick_params(axis='y', which='both', left=False, labelleft=False)  # Turn off y-axis ticks and labels
        else:
            plt.axis('off')
        # Save
        # plt.savefig(OUTDIR / f'{filename}.png', dpi=100)
        plt.savefig(OUTDIR / f'{filename} - small.png', bbox_inches='tight', dpi=100)
    else:
        # Labels
        plt.xlabel(xlab)
        plt.ylabel(ylab)
        # Save
        plt.savefig(OUTDIR / f'{filename}.png', dpi=100)
    plt.clf()


# todo: could be DRYer
# todo: if dev data useful: consider dev + non-dev in same plot
def plots(df: pd.DataFrame, df_dev0: pd.DataFrame, small=False, dev_data_plots=False):
    """Plots"""
    # Histogram: Value set n selections
    # - Size distribution histogram. How many code sets in initial call of log session
    datasets = ((df, 'Dev data included'), (df_dev0, '')) if dev_data_plots else ((df_dev0, ''),)
    for df_i, name_suffix in datasets:
        # Title
        title = f'Code set comparison size{f" - {name_suffix}" if name_suffix else ""}'
        # Select data
        df_i2 = df_i[df_i['api_call'] == 'get-csets']
        df_i2['len_codeset_ids'] = df_i['codeset_ids'].apply(lambda x: len(x))
        data: List[int] = list(df_i2['len_codeset_ids'])
        bins = range(min(data), max(data) + 2)
        # Render
        plot_render(data, title, 'Number of code sets being compared', 'Frequency', bins, small)

    # Histogram: API calls per week
    for df_i, name_suffix in datasets:
        # Title
        title = f'API calls per week{f" - {name_suffix}" if name_suffix else ""}'
        # Select data
        # for df, name_suffix in ((df_apiruns, 'Dev data included'), (df_apiruns_dev0, '')):
        data: List = list(df_i['week'])
        bins = len(set(data))
        # Render
        plot_render(data, title, 'Week', 'API calls', bins, small, is_timeseries=True)

    # Histogram: Duration, session API calls
    # df_i = df  # dev data ok for this one, but for some reason not rendering
    df_i = df_dev0
    # Title
    title = f'Duration, session API calls'
    # Select data
    df_i2 = df_i.drop_duplicates(subset='group_id', keep='first')
    data: List[float] = df_i2['duration_seconds_float'].tolist()
    # noinspection PyTypeChecker
    data = [x for x in data if x]  # filter null ''s
    # data = [round(x, 1) for x in data]  # lower decimal precision didn't make any diff
    # - int or deca seconds also didn't make a difference
    bins = 50
    # Render
    plot_render(
        data, title, 'n seconds', 'n sessions', bins, small, log_scale=True, xtick_step=10)

    # Histogram: Session duration divided by concept count
    # todo: alternate view where I have n concepts on y axis, and n seconds on x
    # df_i = df  # dev data should've been ok, but were many outliers
    df_i = df_dev0
    # Title
    title = f'Session API call duration / concept count'
    # Select data
    df_i2 = df_i.drop_duplicates(subset='group_id', keep='first')  # df_dev0: len 1550 --> 542
    df_i2 = df_i2[~df_i2['duration_sec_per_concept'].isin([np.inf, -np.inf, ''])]  # idk how '' snuck in
    data: List[float] = df_i2['duration_sec_per_concept'].tolist()
    # noinspection PyTypeChecker
    data = [x for x in data if x]  # filter null ''s
    bins = 30
    # Render
    plot_render(
        data, title, 'n seconds / concept', 'instances', bins, small, log_scale=True)

    # Histogram: User queries - calls
    # todo #1: DRY up w/ other user queries section(s)
    #  - remove '# noinspection DuplicatedCode' after
    # df_i = df_dev0
    # Select data
    # noinspection DuplicatedCode
    # ip_counts = {}
    # ips = df_i['client_ip'].to_list()
    # for ip in ips:
    #     ip_counts[ip] = ip_counts.get(ip, 0) + 1
    # data = list(ip_counts.values())
    # # Variation: binning
    # bins = int(max(data) / 3)
    # title = f'N queries made by users'
    # plot_render(
    #     data, title, 'N queries', 'N users', bins, small, log_scale=False, xtick_step=10)
    # # Variation: no binning
    # bins = max(data)
    # title = f'N queries made by users - No bins'
    # plot_render(
    #     data, title, 'API calls', 'Number of users', bins, small, log_scale=True, xtick_step=10)

    # Histogram: User queries - sessions
    df_i = df_dev0
    df_i2 = df_i.drop_duplicates(subset='group_id', keep='first')  # df_dev0: len 1550 --> 542
    # Select data
    # noinspection DuplicatedCode
    ip_counts = {}
    ips = df_i2['client_ip'].to_list()
    for ip in ips:
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    data = list(ip_counts.values())
    # Plot
    bins = max(data)
    title = f'VS-Hub use distribution'
    plot_render(
        data, title, 'VS-Hub page visits', 'Number of users', bins, small, log_scale=False, xtick_step=5)

    # Histogram: User queries - days
    df_i = df_dev0
    df_i2 = df_i.drop_duplicates(subset=['client_ip', 'date'], keep='first')
    # Select data
    # noinspection DuplicatedCode
    ip_counts = {}
    ips = df_i2['client_ip'].to_list()
    for ip in ips:
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    data = list(ip_counts.values())
    # Plot
    bins = max(data)
    title = f'User active days'
    plot_render(
        data, title, 'n distinct days active', 'n users', bins, small, log_scale=True, xtick_step=1)


def run(use_cache=False, verbose=False, dev_data_plots=False):
    """Run analysis

    :param use_cache: If True, will use most recent local CSV instead of calling the database"""
    # Initial setup ---
    t0 = datetime.now()
    setup()
    # api_runs_query uses apiruns_plus which has dev data
    df_apiruns_dev1: pd.DataFrame = get_dataset_with_mods(api_runs_query, USAGE_UNJOINED_CSV_PATH, use_cache, verbose)
    # usage_query uses apijoin which has no dev data
    df_dev0: pd.DataFrame = get_dataset_with_mods(usage_query, USAGE_JOINED_CSV_PATH, use_cache, verbose)
    # TODO: consider filtering out the dev data from the 3am gh actions:
    # df_apiruns_dev0: pd.DataFrame = filter_dev_data(df_apiruns_dev1, verbose)
    # df_w_groups_filtered_dev0: pd.DataFrame = filter_dev_data(df_w_groups_filtered, verbose)

    df_out: pd.DataFrame = summary_stats(df_apiruns_dev1, df_dev0)
    # Table ---
    # Stats: With dev IPs included
    # df_out_dev1: pd.DataFrame = summary_stats(df_apiruns_dev1, df_w_groups_filtered)

    # Stats: With dev IPs filtered out
    # df_out_dev0: pd.DataFrame = summary_stats(df_apiruns_dev0, df_w_groups_filtered_dev0)

    # Join different output datasets
    # df_out = df_out_dev1.merge(df_out_dev0.rename(columns={'Value': 'Value_no_dev'}), on='Measure', how='outer')
    df_out.to_csv(OUT_CSV_PATH_ALL, index=False)

    # Plots ---
    # - From primary datasets
    # todo: would be better to combine dev0/dev1 and small(T/F) here and then make 1 call to plot() for each combo
    #  - would need refactor 'for df, name_suffix in' out of plot()
    plots(df_apiruns_dev1, df_dev0, False, dev_data_plots)  # Big
    plots(df_apiruns_dev1, df_dev0, True, dev_data_plots)  # Small
    if verbose:
        print(f'Finished stats report in n seconds: {(datetime.now() - t0).seconds}')

    # - From custom queries
    for log_scale in (True, False):
        plot_concepts_in_calls(log_scale)


if __name__ == '__main__':
    run()
