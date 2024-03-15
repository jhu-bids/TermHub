"""AMIA paper 2024: Statistics

todo's (minor)
 - get_dataset_with_mods(): Messy to have fetching of dataset and also modification in 1 function. This adds client IP.

Resources
- GH issue: https://github.com/jhu-bids/TermHub/issues/631
- Paper: https://livejohnshopkins-my.sharepoint.com/:w:/g/personal/sgold15_jh_edu/EXbuxwBsb0pPgFfgPYjR6qgBlJ1gmpqsMPYJ3vn6Y_HnYw?e=4%3ApEDbMe&fromShare=true&at=9&CID=d4663c40-1ebe-db59-8cf5-2bc091d45692"""
import os
import sys
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Callable, Dict, List, Union

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

    if not OUTDIR.exists():
        OUTDIR.mkdir()


def api_runs_query(verbose=False):
    """Get all records from api_runs table"""
    t0 = datetime.now()
    with get_db_connection() as con:
        data: List[RowMapping] = sql_query(
            con, """
                SELECT DISTINCT *,
                date_bin('1 week', timestamp::TIMESTAMP, TIMESTAMP '2023-10-30')::date week,
                timestamp::date date FROM public.api_runs r""")
    data: List[Dict] = [dict(d) for d in data]
    if verbose:
        print(f'api_runs_query(): Fetched {len(data)} records in n seconds: {(datetime.now() - t0).seconds}')
    return data


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
    df['client_ip'] = df['client'].apply(lambda x: x.split(':')[0])
    # Filtering
    df = preprocess_null_call_groups(df, verbose)
    # Formatting
    df = df.fillna('')  # fixes problem w/ .str.contains() ops
    return df


def preprocess_dev_ips(df: pd.DataFrame, verbose=True) -> pd.DataFrame:
    """Preprocess data: remove developers"""
    # Devs accessing dev/prod
    developer_ips = {'Siggie': '216.164.48.98', 'Joe': '174.99.54.40'}
    if verbose:
        print('Filtered out n records based on IP addresses of each developer accesing dev/prod:')
        for dev, ip in developer_ips.items():
            df_i = df[df['client_ip'] == ip]
            print(f'  - {dev}: {len(df_i)}')
    df2 = df[~df['client_ip'].isin(list(developer_ips.values()))]
    # Devs running locally
    count_before = len(df2)
    df2 = df2[df2['host'].isin(['dev', 'prod'])]
    if verbose:
        print('Filtered out n records based devs running locally: ',  count_before - len(df2))
    return df2

def preprocess_null_call_groups(df: pd.DataFrame, verbose=True) -> pd.DataFrame:
    """Preprocess data: remove null api_call_group_id

    These are cases from before we added this feature, or where we called the backend directly.

    As of 2024/03/14 this doesn't have an effect. No NULL groups."""
    df2 = df[~df['api_call_group_id'].isna()]
    if verbose:
        print(f'Filtered out n records based on null api_call_group_id: ', len(df) - len(df2))
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
    summary['Log records with session id'] = len(df_w_groups_filtered)
    summary['Log sessions'] = len(df_w_groups_filtered['api_call_group_id'].unique())
    summary['IP addresses'] = len(df_apiruns['client_ip'].unique())
    summary['Sessions with errors'] = df_w_groups_filtered[df_w_groups_filtered['result'].str.lower().str.contains('error')][
        'api_call_group_id'].nunique()
    summary['All API call errors'] = len(df_apiruns[df_apiruns['result'].str.lower().str.contains('error')])

    # Value set combos
    df_get_csets = df_w_groups_filtered[df_w_groups_filtered['api_call'] == 'get-csets']
    summary['Value set combos'] = len(set([tuple(x) for x in df_get_csets['codeset_ids']]))

    # todo: temp: analysis
    #  - analyze uniqueness of get-csets calls within an API call group session
    # diff_get_csets_vs_groups=35; i feel like this should be equal to some calc involving next 4 vars, but not sure
    # noinspection PyUnusedLocal
    diff_get_csets_vs_groups = len(df_get_csets) - len(df_get_csets['api_call_group_id'].unique())  # 35
    diff_codeset_ids_in_group__n_instances = 0  # 1
    diff_codeset_ids_in_group__n_calls = 0  # 2
    mult_get_cset_in_session__n_instances = 0  # 30
    mult_get_cset_in_session__n_calls = 0  # 64
    # todo: maybe convert to str in pre-processing instead, if need 'str' more than temporarily
    df_get_csets['codeset_ids'] = df_get_csets['codeset_ids'].astype(str)
    for group_id, group_data in df_get_csets.groupby('api_call_group_id'):
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


def run(use_cache=False, verbose=False):
    """Run analysis

    :param use_cache: If True, will use most recent local CSV instead of calling the database"""
    # Initial setup ---
    setup()
    df_apiruns: pd.DataFrame = get_dataset_with_mods(api_runs_query, USAGE_UNJOINED_CSV_PATH, use_cache, verbose)
    df_w_groups_filtered: pd.DataFrame = get_dataset_with_mods(usage_query, USAGE_JOINED_CSV_PATH, use_cache, verbose)
    df_apiruns_dev0: pd.DataFrame = preprocess_dev_ips(df_apiruns, verbose)
    df_w_groups_filtered_dev0: pd.DataFrame = preprocess_dev_ips(df_w_groups_filtered, verbose)

    # Table ---
    # Stats: With dev IPs included
    df_out_dev1: pd.DataFrame = summary_stats(df_apiruns, df_w_groups_filtered)

    # Stats: With dev IPs filtered out
    df_out_dev0: pd.DataFrame = summary_stats(df_apiruns_dev0, df_w_groups_filtered_dev0)

    # Join different output datasets
    df_out = df_out_dev1.merge(df_out_dev0.rename(columns={'Value': 'Value_no_dev'}), on='Measure', how='outer')
    df_out.to_csv(OUT_CSV_PATH_ALL, index=False)

    # Plots ---
    # todo: consider dev + non-dev in same plot
    # Histogram: Value set n selections
    # - Size distribution histogram. How many code sets in initial call of log session
    for df, name_suffix in ((df_w_groups_filtered, 'Dev data included'), (df_w_groups_filtered_dev0, '')):
        df_i = df[df['api_call'] == 'get-csets']
        df_i['len_codeset_ids'] = df_i['codeset_ids'].apply(lambda x: len(x))
        data = list(df_i['len_codeset_ids'])
        plt.hist(data, bins=range(min(data), max(data) + 1), edgecolor='black', alpha=0.7)
        plt.xlabel('Number of code sets being compared')
        plt.ylabel('Frequency')
        title_affix = f' - {name_suffix}' if name_suffix else ''
        title = f'Code set comparison size{title_affix}'
        filename = title.replace(' ', '_').lower()
        plt.title(title)
        if verbose:
            plt.show()
        plt.savefig(OUTDIR / f'{filename}.png')
        plt.clf()

    for df, name_suffix in ((df_w_groups_filtered, 'Dev data included'), (df_w_groups_filtered_dev0, '')):
    # for df, name_suffix in ((df_apiruns, 'Dev data included'), (df_apiruns_dev0, '')):
        data = list(df['week'])
        plt.hist(data, bins=len(set(data)), edgecolor='black', alpha=0.7)
        plt.xlabel('Week')
        plt.ylabel('API calls')
        title_affix = f' - {name_suffix}' if name_suffix else ''
        title = f'API calls per week{title_affix}'
        filename = title.replace(' ', '_').lower()
        plt.title(title)
        if verbose:
            plt.show()
        plt.savefig(OUTDIR / f'{filename}.png')
        plt.clf()
    print()


if __name__ == '__main__':
    run()

"""
other queries:

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


SELECT host,client,result, replace(result, ' rows', '') concept_ids, week,api_call_group_id
FROM public.apijoin
WHERE api_call = 'codeset-ids-by-concept-id'

with c1 as (
  SELECT replace(result, ' rows', '') cnt FROM public.apijoin
  WHERE api_call IN ('codeset-ids-by-concept-id', 'concept', 'get-cset-members-items')
), c2 as (
  SELECT CASE WHEN cnt ~ '^[0-9]+$' THEN cnt::integer ELSE NULL END AS cnt FROM c1
)
select 10^round(log10(cnt)) || ' - ' || 10 * 10^round(log10(cnt)) - 1 concepts_in_call, count(*) calls
from c2 group by 1 order by 1 desc;

result, modified
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