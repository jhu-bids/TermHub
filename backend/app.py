"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
import os
from pathlib import Path
from subprocess import call as sp_call
from typing import Any, Dict, List, Union, Callable, Set
from functools import cache

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from enclave_wrangler.datasets import run_favorites as update_termhub_csets

DEBUG = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent
CSV_PATH = f'{PROJECT_DIR}/termhub-csets/datasets/prepped_files/'
DS = None  # Contains all the datasets as a dict
ds = None  # Contains all datasets, transformed datasets, and a few functions as a nameespace

def load_dataset(ds_name):
    try:
        path = os.path.join(CSV_PATH, ds_name + '.csv')
        print(f'loading {path}')
        ds = pd.read_csv(path, keep_default_na=False)
        return ds
    except FileNotFoundError as err:
        raise err
    except Exception as err:
        print(f'failed loading {path}')
        raise err


class Bunch(object):    # dictionary to namespace, a la https://stackoverflow.com/a/2597440/1368860
  def __init__(self, adict):
    self.__dict__.update(adict)


def cnt(vals):
    return len(set(vals))


def commify(n):
    return f'{n:,}'


def filter(msg, ds, dfname, func, cols):
    df = ds.__dict__[dfname]
    before = { col: cnt(df[col]) for col in cols }

    ds.__dict__[dfname] = func(df)
    if ds.__dict__[dfname].equals(df):
        log_counts(f'{msg}. No change.', **before)
    else:
        log_counts(f'{msg}. Before', **before)
        after = { col: cnt(df[col]) for col in cols }
        log_counts(f'{msg}. After', **after)
        # change = { col: (after[col] - before[col]) / before[col] for col in cols }


def _log_counts():
    msgs = []
    def __log_counts(msg=None, concept_set_name=None, codeset_id=None, concept_id=None):
        if msg:
            msgs.append([msg, *[int(n) if n else None for n in [concept_set_name, codeset_id, concept_id]]])
        return msgs
    return __log_counts


log_counts = _log_counts()


def load_globals():
    """
    expose tables and other stuff in namespace for convenient reference
        links                   # concept_relationship grouped by concept_id_1, subsumes only
        child_cids()            # function returning all the concept_ids that are
                                #   children (concept_id_1) of a concept_id
        connect_children()      # function returning concept hierarchy. see #139
                                #   (https://github.com/jhu-bids/TermHub/issues/139)
                                #   currently doing lists of tuples, will probably
                                #   switch to dict of dicts
    """
    ds = Bunch(DS)

    # TODO: try this later. will require filtering other stuff also? This will be useful for provenance
    # ds.data_messages = []
    other_msgs = []

    log_counts('concept_set_container', concept_set_name=cnt(ds.concept_set_container.concept_set_name))
    log_counts('code_sets',
               concept_set_name=cnt(ds.code_sets.concept_set_name),
               codeset_id=cnt(ds.code_sets.codeset_id))
    log_counts('concept_set_members',
               concept_set_name=cnt(ds.concept_set_members.concept_set_name),
               codeset_id=cnt(ds.concept_set_members.codeset_id),
               concept_id=cnt(ds.concept_set_members.concept_id))
    log_counts('concept_set_version_item',
               concept_set_name=cnt(ds.concept_set_members.concept_set_name),
               codeset_id=cnt(ds.concept_set_version_item.codeset_id),
               concept_id=cnt(ds.concept_set_version_item.concept_id))
    log_counts('intersection(containers, codesets)',
               concept_set_name=len(set.intersection(set(ds.concept_set_container.concept_set_name),
                                                     set(ds.code_sets.concept_set_name))))
    log_counts('intersection(codesets, members, version_items)',
               codeset_id=len(set.intersection(set(ds.code_sets.codeset_id),
                                               set(ds.concept_set_members.codeset_id),
                                               set(ds.concept_set_version_item.codeset_id))))
    log_counts('intersection(codesets, version_items)',
               codeset_id=len(set.intersection(set(ds.code_sets.codeset_id),
                                               set(ds.concept_set_version_item.codeset_id))))
    log_counts('intersection(members, version_items)',
               codeset_id=len(set.intersection(set(ds.concept_set_members.codeset_id),
                                               set(ds.concept_set_version_item.codeset_id))),
               concept_id=len(set.intersection(set(ds.concept_set_members.concept_id),
                                               set(ds.concept_set_version_item.concept_id))))

    codeset_ids = set(ds.concept_set_version_item.codeset_id)

    filter('weird that there would be versions (in code_sets and concept_set_members) '
                        'that have nothing in concept_set_version_item...filtering those out',
           ds, 'code_sets', lambda df: df[df.codeset_id.isin(codeset_ids)], ['codeset_id'])

    # no change (2022-10-23):
    filter('concept_set_container filtered to exclude archived',
           ds, 'concept_set_container', lambda df: df[~ df.archived], ['concept_set_name'])

    #
    filter('concept_set_members filtered to exclude archived',
           ds, 'concept_set_members', lambda df: df[~ df.archived], ['codeset_id', 'concept_id'])

    concept_set_names = set.intersection(
                            set(ds.concept_set_container.concept_set_name),
                            set(ds.code_sets.concept_set_name))

    # csm_archived_names = set(DS['concept_set_members'][DS['concept_set_members'].archived].concept_set_name)
    # concept_set_names = concept_set_names.difference(csm_archived_names)

    # no change (2022-10-23):
    filter('concept_set_container filtered to have matching code_sets/versions',
           ds, 'concept_set_container', lambda df: df[df.concept_set_name.isin(concept_set_names)], ['concept_set_name'])

    filter('code_sets filtered to have matching concept_set_container',
           ds, 'code_sets', lambda df: df[df.concept_set_name.isin(concept_set_names)], ['concept_set_name'])

    codeset_ids = set.intersection(set(ds.code_sets.codeset_id),
                                   set(ds.concept_set_version_item.codeset_id))
    filter(
        'concept_set_members filtered to filtered code_sets', ds, 'concept_set_members',
        lambda df: df[df.codeset_id.isin(set(ds.code_sets.codeset_id))], ['codeset_id', 'concept_id'])

    # Filters out any concepts/concept sets w/ no name
    filter('concept_set_members filtered to exclude concept sets with empty names',
            ds, 'concept_set_members',
           lambda df: df[~df.archived],
           ['codeset_id', 'concept_id'])

    filter('concept_set_members filtered to exclude archived concept set.',
           ds, 'concept_set_members',
           lambda df: df[~df.archived],
           ['codeset_id', 'concept_id'])

    ds.concept_relationship = ds.concept_relationship_subsumes_only
    other_msgs.append('only using subsumes relationships in concept_relationship')

    # I don't know why, there's a bunch of codesets that have no concept_set_version_items:
    # >>> len(set(ds.concept_set_members.codeset_id))
    # 3733
    # >>> len(set(ds.concept_set_version_item.codeset_id))
    # 3021
    # >>> len(set(ds.concept_set_members.codeset_id).difference(set(ds.concept_set_version_item.codeset_id)))
    # 1926
    # should just toss them, right?

    # len(set(ds.concept_set_members.concept_id))             1,483,260
    # len(set(ds.concept_set_version_item.concept_id))          429,470
    # len(set(ds.concept_set_version_item.concept_id)
    #     .difference(set(ds.concept_set_members.concept_id)))   19,996
    #
    member_concepts = set(ds.concept_set_members.concept_id)
        #.difference(set(ds.concept_set_version_item))

    ds.concept_set_version_item = ds.concept_set_version_item[
        ds.concept_set_version_item.concept_id.isin(member_concepts)]

    # only need these two columns now:
    ds.concept_set_members = ds.concept_set_members[['codeset_id', 'concept_id']]

    ds.all_related_concepts = set(ds.concept_relationship.concept_id_1).union(
                                set(ds.concept_relationship.concept_id_2))
    all_findable_concepts = member_concepts.union(ds.all_related_concepts)

    ds.concept.drop(['domain_id', 'vocabulary_id', 'concept_class_id', 'standard_concept', 'concept_code',
                      'invalid_reason', ], inplace=True, axis=1)

    ds.concept = ds.concept[ds.concept.concept_id.isin(all_findable_concepts)]

    ds.links = ds.concept_relationship.groupby('concept_id_1')
    # ds.all_concept_relationship_cids = set(ds.concept_relationship.concept_id_1).union(set(ds.concept_relationship.concept_id_2))

    @cache
    def child_cids(cid):
        """Return list of `concept_id_2` for each `concept_id_1` (aka all its children)"""
        if cid in ds.links.groups.keys():
            return [int(c) for c in ds.links.get_group(cid).concept_id_2.unique() if c != cid]
    ds.child_cids = child_cids

    # @cache
    def connect_children(pcid, cids):  # how to declare this should be tuple of int or None and list of ints
        if not cids:
            return None
        pcid in cids and cids.remove(pcid)
        pcid_kids = {int(cid): child_cids(cid) for cid in cids}
        # pdump({'kids': pcid_kids})
        return {cid: connect_children(cid, kids) for cid, kids in pcid_kids.items()}

    ds.connect_children = connect_children

    # Take codesets, and merge on container. Add to each version.
    # Some columns in codeset and container have the same name, so suffix is needed to distinguish them
    # ...The merge on `concept_set_members` is used for concept counts for each codeset version.
    #   Then adding cset usage counts
    all_csets = (
        ds
            .code_sets.merge(ds.concept_set_container, suffixes=['_version', '_container'],
                             on='concept_set_name')
            .merge(ds.concept_set_members
                        .groupby('codeset_id')['concept_id']
                            .nunique()
                            .reset_index()
                            .rename(columns={'concept_id': 'concepts'}), on='codeset_id')
            .merge(ds.concept_set_counts_clamped, on='codeset_id')
    )
    all_csets = all_csets[[
        'codeset_id', 'concept_set_version_title', 'is_most_recent_version', 'intention_version', 'intention_container',
        'limitations', 'issues', 'update_message', 'has_review', 'provenance', 'authoritative_source', 'project_id',
        'status_version', 'status_container', 'stage', 'archived', 'concepts',
        'approx_distinct_person_count', 'approx_total_record_count', ]]
    all_csets = all_csets.drop_duplicates()
    ds.all_csets = all_csets

    print('added usage counts to code_sets')

    """
        Term usage is broken down by domain and some concepts appear in multiple domains.
        (each concept has only one domain_id in the concept table, but the same concept might
        appear in condition_occurrence and visit and procedure, so it would have usage counts
        in multiple domains.) We can sum total_counts across domain, but not distinct_person_counts
        (possible double counting). So, for now at least, distinct_person_count will appear as a 
        comma-delimited list of counts -- which, of course, makes it hard to use in visualization.
        Maybe we should just use the domain with the highest distinct person count? Not sure.
    """
    # df = df[df.concept_id.isin([9202, 9201])]
    domains = {
        'drug_exposure': 'd',
        'visit_occurrence': 'v',
        'observation': 'o',
        'condition_occurrence': 'c',
        'procedure_occurrence': 'p',
        'measurement': 'm'
    }
    ds.deidentified_term_usage_by_domain_clamped['domain'] = \
        [domains[d] for d in ds.deidentified_term_usage_by_domain_clamped.domain]

    g = ds.deidentified_term_usage_by_domain_clamped.groupby(['concept_id'])
    concept_usage_counts = (
        g.size().to_frame(name='domain_cnt')
         .join(g.agg(
                    total_count=('total_count', sum),
                    domain=('domain', ','.join),
                    distinct_person_count=('distinct_person_count', lambda x: ','.join([str(c) for c in x]))
                ))
        .reset_index())
    print('combined usage counts across domains')

    # c = ds.concept.reset_index()
    # cs = c[c.concept_id.isin([9202, 9201, 4])]
    ds.concept = (
        ds.concept.drop(['valid_start_date','valid_end_date'], axis=1)
            .merge(concept_usage_counts, on='concept_id', how='left')
            .fillna({'domain_cnt': 0, 'domain': '', 'total_count': 0, 'distinct_person_count': 0})
            .astype({'domain_cnt': int, 'total_count': int})
            # .set_index('concept_id')
    )
    print('Done building global ds objects')
    return ds

# todo: consider: run 2 backend servers, 1 to hold the data and 1 to service requests / logic? probably.
# TODO: #2: remove try/except when git lfs fully set up
# try:
# todo: temp until we decide if this is the correct way

# dataset_names = list(FAVORITE_DATASETS.keys()) + ['concept_relationship_is_a']

dataset_names = ['concept_set_members',
                 'concept',
                 'concept_relationship_subsumes_only',
                 'concept_set_container',
                 'code_sets',
                 'concept_set_version_item',
                 'deidentified_term_usage_by_domain_clamped',
                 'concept_set_counts_clamped']

try:
    DS = {name: load_dataset(name) for name in dataset_names}
    ds = load_globals()
    #  TODO: Fix this warning? (Joe: doing so will help load faster, actually)
    #   DtypeWarning: Columns (4) have mixed types. Specify dtype option on import or set low_memory=False.
    #   keep_default_na fixes some or all the warnings, but doesn't manage dtypes well.
    #   did this in termhub-csets/datasets/fixing-and-paring-down-csv-files.ipynb:
    #   csm = pd.read_csv('./concept_set_members.csv',
    #                    # dtype={'archived': bool},    # doesn't work because of missing values
    #                   converters={'archived': lambda x: x and True or False}, # this makes it a bool field
    #                   keep_default_na=False)

    #  TODO: try to fix.... not working yet:
    # code_set.version got mangled into version numbers like 1.0, 2.0
    #
    # converters = {
    #     'int': lambda v: v.astype(int)
    # }
    # def bool_converter(v):
    #     return v and True or False
    #
    # csv_opts = {
    #     # 'code_sets': {'dtype': {'version': int}}
    #     'code_sets': {'converters': {'version': converters['int']}}
    # }
    #
    # df = pd.read_csv(os.path.join(CSV_PATH, 'code_sets' + '.csv'), **(csv_opts['code_sets']))
except FileNotFoundError:
    # todo: what if they haven't downloaded? maybe need to ls files and see if anything needs to be downloaded first
    update_termhub_csets(transforms_only=True)
    DS = {name: load_dataset(name) for name in dataset_names}
    ds = load_globals()
print(f'Favorite datasets loaded: {list(DS.keys())}')
# todo: pandasql better?
# PYSQLDF = lambda q: sqldf(q, globals()) # I think you need to call this in the function you're using it in
# COUNTS = PYSQLDF("""
#     SELECT vocabulary_id, COUNT(*) AS cnt
#     FROM CONCEPT
#     GROUP BY 1""")
#except Exception as err:
#    print(f'failed loading datasets', err)

# @cache
def data_stuff_for_codeset_ids(codeset_ids):
    """
    for specific codeset_ids:
        subsets of tables:
            df_code_set_i
            df_concept_set_members_i
            df_concept_relationship_i
        and other stuff:
            concept_ids             # union of all the concept_ids across the requested codesets
            related                 # sorted list of related concept sets
            codesets_by_concept_id  # lookup codeset_ids a concept_id belongs to (in dsi instead of ds because of possible performance impacts)
            top_level_cids          # concepts in selected codesets that have no parent concepts in this group
            cset_name_columns       #

    """
    dsi = Bunch({})

    print(f'data_stuff_for_codeset_ids({codeset_ids})')

    dsi.code_sets_i = ds.code_sets[ds.code_sets['codeset_id'].isin(codeset_ids)]

    dsi.concept_set_members_i = ds.concept_set_members[ds.concept_set_members['codeset_id'].isin(codeset_ids)]

    dsi.concept_set_version_item_i = ds.concept_set_version_item[ds.concept_set_version_item['codeset_id'].isin(codeset_ids)]

    dsi.concept_relationship_i = ds.concept_relationship[
        (ds.concept_relationship.concept_id_1.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_2.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_1 != ds.concept_relationship.concept_id_2)
        # & (ds.concept_relationship.relationship_id == 'Subsumes')
        ]

    # Get related codeset IDs
    selected_concept_ids: Set[int] = set(dsi.concept_set_members_i.concept_id.unique())
    related_codeset_ids = set(ds.concept_set_members[
        ds.concept_set_members.concept_id.isin(selected_concept_ids)].codeset_id)

    dsi.related_csets = (
      ds.all_csets[ds.all_csets['codeset_id'].isin(related_codeset_ids)]
        .merge(ds.concept_set_members, on='codeset_id')
        .groupby(list(ds.all_csets.columns))['concept_id']
        .agg(intersecting_concepts=lambda x: len(set(x).intersection(selected_concept_ids)))
        .reset_index()
        .convert_dtypes({'intersecting_concept_ids': 'int'})
        .assign(recall=lambda row: row.intersecting_concepts / len(selected_concept_ids),
                precision=lambda row: row.intersecting_concepts / row.concepts,
                selected= lambda row: row.codeset_id.isin(codeset_ids))
        .sort_values(by=['selected', 'concepts'], ascending=False)
    )

    # all_csets['selected'] = all_csets['codeset_id'].isin(codeset_ids)
    # all_csets = all_csets.sort_values(by=['selected', 'concepts'], ascending=False)
    dsi.selected_csets = dsi.related_csets[dsi.related_csets['codeset_id'].isin(codeset_ids)]


    # Get relationships for selected code sets
    dsi.links = dsi.concept_relationship_i.groupby('concept_id_1')

    # Get child `concept_id`s
    @cache
    def child_cids(cid):
        """Closure for geting child concept IDs"""
        if cid in dsi.links.groups.keys():
            return [int(c) for c in dsi.links.get_group(cid).concept_id_2.unique() if c != cid]
    dsi.child_cids = child_cids

    # @cache
    def connect_children(pcid, cids):  # how to declare this should be tuple of int or None and list of ints
        if not cids:
            return None
        pcid in cids and cids.remove(pcid)
        pcid_kids = {int(cid): child_cids(cid) for cid in cids}
        # pdump({'kids': pcid_kids})
        return {cid: connect_children(cid, kids) for cid, kids in pcid_kids.items()}
    dsi.connect_children = connect_children

    # Top level concept IDs for the root of our flattened hierarchy
    # dsi.top_level_cids = list(
    #     dsi.concept_relationship_i[
    #         ~ dsi.concept_relationship_i.concept_id_1.isin(dsi.concept_relationship_i.concept_id_2)
    #     ].concept_id_1.unique())

    dsi.top_level_cids = ( set(dsi.concept_set_members_i.concept_id)
                            .difference(set(dsi.concept_relationship_i.concept_id_2)))

    # For a given `concept_id`, get a list of `codeset_id` that it appears in
    dsi.codesets_by_concept_id = dsi.concept_set_members_i[['concept_id', 'codeset_id']] \
        .drop_duplicates() \
        .set_index('codeset_id') \
        .groupby('concept_id').groups
    for cid, codeset_ids in dsi.codesets_by_concept_id.items():
        dsi.codesets_by_concept_id[cid] = [int(codeset_id) for codeset_id in codeset_ids]

    # dsi.concept = ds.concept[ds.concept.concept_id.isin(ds.all_related_concepts)].head(5000) #.union(selected_concept_ids))]

    return dsi

@cache
def parse_codeset_ids(qstring):
    if not qstring:
        return []
    requested_codeset_ids = qstring.split('|')
    requested_codeset_ids = [int(x) for x in requested_codeset_ids]
    return requested_codeset_ids

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)


@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list


# @APP.get("/cset-versions")
# def csetVersions() -> Union[Dict, List]:
#     csm = DS['code_sets']
#     # todo: would be nicer to do this in a cleaner, shorter way, e.g.:
#     # g = csm[['concept_set_name', 'codeset_id', 'version']].groupby('concept_set_name').agg(dict)
#     g: Dict[List[Dict[str, int]]] = {}
#     concept_set_names = list(csm['concept_set_name'].unique())
#     for cs_name in concept_set_names:
#         csm_i = csm[csm['concept_set_name'] == cs_name]
#         for _index, row in csm_i.iterrows():
#             version: int = int(float(row['version'])) if row['version'] else None
#             codeset_id: int = row['codeset_id']
#             if not version:
#                 continue
#             if cs_name not in g:
#                 g[cs_name] = []
#             g[cs_name].append({'version': version, 'codeset_id': codeset_id})
#
#     return g


@APP.get("/get-all-csets")
def get_all_csets() -> Union[Dict, List]:
  return ds.all_csets.to_dict(orient='records')


# TODO: the following is just based on concept_relationship
#       should also check whether relationships exist in concept_ancestor
#       that aren't captured here
# TODO: Add concepts outside the list of codeset_ids?
#       Or just make new issue for starting from one cset or concept
#       and fanning out to other csets from there?
# Example: http://127.0.0.1:8000/cr-hierarchy?codeset_id=818292046&codeset_id=484619125&codeset_id=400614256
@APP.get("/cr-hierarchy")  # maybe junk, or maybe start of a refactor of above
def cr_hierarchy(
    rec_format: str='default',
    codeset_id: Union[str, None] = Query(default=''),
) -> Dict:

    print(ds)
    requested_codeset_ids = parse_codeset_ids(codeset_id)
    # A namespace (like `ds`) specifically for these codeset IDs.
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)

    c = dsi.connect_children(-1, dsi.top_level_cids)

    cids = set([])
    if c:
        cids = set([int(str(k).split('.')[-1]) for k in pd.json_normalize(c).to_dict(orient='records')[0].keys()])
    concepts = ds.concept[ds.concept.concept_id.isin(cids.union(set(dsi.concept_set_members_i.concept_id)))]

    result = {
              # 'all_csets': dsi.all_csets.to_dict(orient='records'),
              'related_csets': dsi.related_csets.to_dict(orient='records'),
              'selected_csets': dsi.selected_csets.to_dict(orient='records'),
              'concept_set_members_i': dsi.concept_set_members_i.to_dict(orient='records'),
              'concept_set_version_item_i': dsi.concept_set_version_item_i.to_dict(orient='records'),
              'hierarchy': c,
              'concepts': concepts.to_dict(orient='records'),
              'data_counts': log_counts(),
    }
    return result
    # result = {
    #     'concept_set_members_i': dsi.concept_set_members_i.to_dict(),
    #     'all_csets': dsi.all_csets.to_dict(),
    #     'hierarchy': c,
    #     'concepts': dsi.concept.to_json(),
    # }
    # return Response(json.dumps(result), media_type="application/json")
    # https://stackoverflow.com/questions/71203579/how-to-return-a-csv-file-pandas-dataframe-in-json-format-using-fastapi/71205127#71205127



@APP.get("/new-hierarchy-stuff")  # maybe junk, or maybe start of a refactor of above
def new_hierarchy_stuff(
        rec_format: str='default',
        codeset_id: Union[str, None] = Query(default=[]), ) -> List[Dict]:

    requested_codeset_ids = parse_codeset_ids(codeset_id)
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)

    links = dsi.concept_relationship_i.groupby('concept_id_1')

    c = ds.connect_children(-1, dsi.top_level_cids)

    """
    TODO: fix comments -- no longer accurate
    
    The only difference between cr_hierarchy and new_hierarchy_stuff is whether the
    child_cids function is from ds or dsi -- that is, is it filtered to codeset_ids or not?
    And the only difference in output appears to be a few records in flattened_concept_hierarchy (used to be `lines`)

           http://127.0.0.1:8000/cr-hierarchy?rec_format=flat&codeset_id=400614256|411456218|419757429|484619125|818292046|826535586
    http://127.0.0.1:8000/new-hierarchy-stuff?rec_format=flat&codeset_id=400614256|411456218|419757429|484619125|818292046|826535586
    {
        # "flattened_concept_hierarchy": [],  // 965 items in cr_hierarchy, 991 items in new_hierarchy_stuff
        "related_csets": [],                // 208 items
        "concept_set_members_i": []         // 1629 items
    }
    I haven't figured out what the difference is yet and whether it matters.
    TODO: come back and figure it out later and generally deal with how to filter in datasets.py and
          which versions of datasets to load, and how hierarchy is generated -- does it include concepts
          outside the selected concept sets or not?
    """

    result = { # 'related_csets': dsi.related.to_dict(orient='records'),
              'concept_set_members_i': json.loads(dsi.concept_set_members_i.to_json(orient='records')),
              'all_csets': json.loads(dsi.all_csets.to_json(orient='records')),
              'hierarchy': c,
              }
    return result


@APP.get("/update-cset")  # maybe junk, or maybe start of a refactor of above
def update_cset(
    codeset_id: int, concept_id: int, state: bool
) -> Dict:
    modification = {'codeset_id': codeset_id, 'concept_id': concept_id, 'state': state}
    print(f'update-cset: {codeset_id}, {concept_id}, {state}')
    return modification


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}


# TODO: Maybe change to `id` instead of row index
@APP.put("/datasets/csets")
def csets_update(d: CsetsUpdate = None) -> Dict:
    """Update cset dataset. Works only on tabular files."""
    # Vars
    result = 'success'
    details = ''
    cset_dir = os.path.join(PROJECT_DIR, 'termhub-csets')
    path_root = os.path.join(cset_dir, 'datasets')

    # Update cset
    # todo: dtypes need to be registered somewhere. perhaps a <CSV_NAME>_codebook.json()?, accessed based on filename,
    #  and inserted here
    # todo: check git status first to ensure clean? maybe doesn't matter since we can just add by filename
    path = os.path.join(path_root, d.dataset_path)
    # noinspection PyBroadException
    try:
        df = pd.read_csv(path, dtype={'id': np.int32, 'last_name': str, 'first_name': str}).fillna('')
        for index, field_values in d.row_index_data_map.items():
            for field, value in field_values.items():
                df.at[index, field] = value
        df.to_csv(path, index=False)
    except BaseException as err:
        result = 'failure'
        details = str(err)

    # Push commit
    # todo?: Correct git status after change should show something like this near end: `modified: FILENAME`
    relative_path = os.path.join('datasets', d.dataset_path)
    # todo: Want to see result as string? only getting int: 1 / 0
    #  ...answer: it's being printed to stderr and stdout. I remember there's some way to pipe and capture if needed
    # TODO: What if the update resulted in no changes? e.g. changed values were same?
    git_add_result = sp_call(f'git add {relative_path}'.split(), cwd=cset_dir)
    if git_add_result != 0:
        result = 'failure'
        details = f'Error: Git add: {d.dataset_path}'
    git_commit_result = sp_call(['git', 'commit', '-m', f'Updated by server: {relative_path}'], cwd=cset_dir)
    if git_commit_result != 0:
        result = 'failure'
        details = f'Error: Git commit: {d.dataset_path}'
    git_push_result = sp_call('git push origin HEAD:main'.split(), cwd=cset_dir)
    if git_push_result != 0:
        result = 'failure'
        details = f'Error: Git push: {d.dataset_path}'

    return {'result': result, 'details': details}


@APP.put("/datasets/vocab")
def vocab_update():
    """Update vocab dataset"""
    pass


# TODO: figure out where we want to put this. models.py? Create route files and include class along w/ route func?
# TODO: Maybe change to `id` instead of row index
class CsetsUpdate(BaseModel):
    """Update concept sets.
    dataset_path: File path. Relative to `/termhub-csets/datasets/`
    row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
      name of the fields to be updated, and values contain the values to update in that particular cell."""
    dataset_path: str = ''
    row_index_data_map: Dict[int, Dict[str, Any]] = {}


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()

def pdump(o):
    print(json.dumps(o, indent=2))
