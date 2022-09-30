"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
import os
import errno
from pathlib import Path
from subprocess import call as sp_call
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
import requests
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
# from pandasql import sqldf
from pydantic import BaseModel

from enclave_wrangler.config import config, FAVORITE_DATASETS

DEBUG = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent
CSV_PATH = f'{PROJECT_DIR}/termhub-csets/datasets/prepped_files/'

def load_dataset(ds_name):
    try:
        path = os.path.join(CSV_PATH, ds_name + '.csv')
        print(f'loading {path}')
        ds = pd.read_csv(path, keep_default_na=False)
        return ds
    except Exception as err:
        print(f'failed loading {path}')
        raise err

# todo: consider: run 2 backend servers, 1 to hold the data and 1 to service requests / logic? probably.
# TODO: #2: remove try/except when git lfs fully set up
try:
    # todo: temp until we decide if this is the correct way
    dataset_names = list(FAVORITE_DATASETS.keys()) + ['concept_relationship_is_a']
    DS = {name: load_dataset(name) for name in dataset_names}
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

    print(f'Favorite datasets loaded: {list(DS.keys())}')
    # todo: pandasql better?
    # PYSQLDF = lambda q: sqldf(q, globals()) # I think you need to call this in the function you're using it in
    # COUNTS = PYSQLDF("""
    #     SELECT vocabulary_id, COUNT(*) AS cnt
    #     FROM CONCEPT
    #     GROUP BY 1""")
except Exception as err:
    print(f'failed loading datasets', err)


class Bunch(object):    # dictionary to namespace, a la https://stackoverflow.com/a/2597440/1368860
  def __init__(self, adict):
    self.__dict__.update(adict)

def make_data_stuff():
    """
    expose tables and other stuff in namespace for convenient reference
        links                   # concept_relationship grouped by concept_id_1, subsumes only
        child_cids()            # function returning all the concept_ids that are
                                #   children (concept_id_1) of a concept_id
        connect_children()      # function returning concept hierarchy. see #139
                                #   (https://github.com/jhu-bids/TermHub/issues/139)
                                #   currently doing lists of tuples, will probably
                                #   switch to dict of dicts
        concept_name_lookup     # lookup by concept_id
        codeset_name_lookup     # lookup by concept_id
    """
    ds = Bunch(DS)

    ds.subsumes = ds.concept_relationship[ds.concept_relationship.relationship_id == 'Subsumes']
    ds.links = ds.subsumes.groupby('concept_id_1')

    def child_cids(cid):
        if cid in ds.links.groups.keys():
            return [int(c) for c in ds.links.get_group(cid).concept_id_2.unique() if c != cid]
    ds.child_cids = child_cids


    def connect_children(pc): # how to declare this should be tuple of int or None and list of ints
        pcid, cids = pc
        pcid in cids and cids.remove(pcid)
        expanded_cids = [ds.child_cids(cid) for cid in cids]
        return (pcid, [connect_children(ec) if type(ec)==tuple else ec for ec in expanded_cids])
    ds.connect_children = connect_children

    ds.concept_name_lookup = ds.concept_set_members[['concept_id', 'concept_name']] \
        .drop_duplicates() \
        .set_index('concept_name') \
        .groupby('concept_id').groups
    # [(cid, len(names)) for cid, names in concept_name_lookup.items() if len(names) > 1]    # should be 1-to-1
    for cid, names in ds.concept_name_lookup.items():
        ds.concept_name_lookup[cid] = names[0]

    ds.codeset_name_lookup = ds.concept_set_members[['codeset_id', 'concept_set_name']] \
        .drop_duplicates() \
        .set_index('concept_set_name') \
        .groupby('codeset_id').groups
    # [(cid, len(names)) for cid, names in concept_name_lookup.items() if len(names) > 1]    # should be 1-to-1
    for cset_id, names in ds.codeset_name_lookup.items():
        ds.codeset_name_lookup[cset_id] = names[0]

    print('Done building global ds objects')
    return ds

ds = make_data_stuff()

def data_stuff_for_codeset_ids(codeset_ids):
    """
    for specific codeset_ids:
        subsets of tables:
            df_code_set_i
            df_concept_set_members_i
            df_concept_relationship_i
        and other stuff:
            csets_info              # code_set_i with container info columns appended
            concept_ids             # union of all the concept_ids across the requested codesets
            related                 # sorted list of related concept sets
            codesets_by_concept_id  # lookup codeset_ids a concept_id belongs to (in dsi instead of ds because of possible performance impacts)
            top_level_cids          # concepts in selected codesets that have no parent concepts in this group
            cset_name_columns       #

    """
    dsi = Bunch({})

    dsi.code_sets_i = ds.code_sets[ds.code_sets['codeset_id'].isin(codeset_ids)]

    dsi.concept_set_members_i = ds.concept_set_members[ds.concept_set_members['codeset_id'].isin(codeset_ids)]

    dsi.concept_relationship_i = ds.concept_relationship[
        (ds.concept_relationship.concept_id_1.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_2.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_1 != ds.concept_relationship.concept_id_2)   &
        (ds.concept_relationship.relationship_id == 'Subsumes')]

    dsi.csets_info = {int(ci['codeset_id']): ci for ci in codeset_info(codeset_ids=codeset_ids, dsi=dsi)}  # append container info columns
    # casting as int here isn't working. in json results, still shows as a string key

    dsi.concept_ids = dsi.concept_set_members_i.concept_id.unique()

    dsi.subsumes = dsi.concept_relationship_i[dsi.concept_relationship_i.relationship_id == 'Subsumes']
    dsi.links = dsi.subsumes.groupby('concept_id_1')

    def child_cids(cid):
        if cid in dsi.links.groups.keys():
            return [int(c) for c in dsi.links.get_group(cid).concept_id_2.unique() if c != cid]
    dsi.child_cids = child_cids

    related_csm = ds.concept_set_members[ds.concept_set_members.concept_id.isin(dsi.concept_ids)]
    c = pd.DataFrame({'selected': related_csm.codeset_id.isin(codeset_ids)})
    related_csm['selected'] = c  # not sure how to get around SettingWithCopyWarning
    dsi.related = related_csm.groupby(['selected', 'codeset_id', 'concept_set_name', 'version']
                                      )['concept_id'].nunique().reset_index() \
        .sort_values(by=['selected','concept_id'], ascending=False).rename(columns={'concept_id': 'concepts'})

    dsi.codesets_by_concept_id = dsi.concept_set_members_i[['concept_id', 'codeset_id']] \
        .drop_duplicates() \
        .set_index('codeset_id') \
        .groupby('concept_id').groups
    for cid, codeset_ids in dsi.codesets_by_concept_id.items():
        dsi.codesets_by_concept_id[cid] = [int(codeset_id) for codeset_id in codeset_ids]


    dsi.top_level_cids = list(dsi.concept_relationship_i[
                              ~dsi.concept_relationship_i.concept_id_1.isin(dsi.concept_relationship_i.concept_id_2)
                          ].concept_id_1.unique())

    dsi.cset_name_columns = {ds.codeset_name_lookup[codeset_id]: u'\N{check mark}' for codeset_id in codeset_ids}

    return dsi

def parse_codeset_ids(qstring):
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


@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list


@APP.get("/cset-versions")
def csetVersions() -> Union[Dict, List]:
    csm = DS['code_sets']
    # todo: would be nicer to do this in a cleaner, shorter way, e.g.:
    # g = csm[['concept_set_name', 'codeset_id', 'version']].groupby('concept_set_name').agg(dict)
    g: Dict[List[Dict[str, int]]] = {}
    concept_set_names = list(csm['concept_set_name'].unique())
    for cs_name in concept_set_names:
        csm_i = csm[csm['concept_set_name'] == cs_name]
        for _index, row in csm_i.iterrows():
            version: int = int(float(row['version'])) if row['version'] else None
            codeset_id: int = row['codeset_id']
            if not version:
                continue
            if cs_name not in g:
                g[cs_name] = []
            g[cs_name].append({'version': version, 'codeset_id': codeset_id})

    return g


# Example: http://127.0.0.1:8000/codeset-info?codeset_id=400614256|411456218|484619125|818292046|826535586
@APP.get("/codeset-info")        # maybe junk, or maybe start of a refactor of above
def codeset_info(codeset_id: Union[str, None] = Query(default=[]), codeset_ids=[], dsi=None) -> List[Dict]:
    """
    join container info onto dsi.code_sets_i     # maybe just do this off the bat for all code sets?
    """

    requested_codeset_ids = codeset_ids or parse_codeset_ids(codeset_id)
    dsi = dsi or data_stuff_for_codeset_ids(requested_codeset_ids)

    df = dsi.code_sets_i.merge(ds.concept_set_container_edited, on='concept_set_name')
    return json.loads(df.to_json(orient='records'))


# TODO: the following is just based on concept_relationship
#       should also check whether relationships exist in concept_ancestor
#       that aren't captured here
# TODO: Add concepts outside the list of codeset_ids?
#       Or just make new issue for starting from one cset or concept
#       and fanning out to other csets from there?
# Example: http://127.0.0.1:8000/cr-hierarchy?codeset_id=818292046&codeset_id=484619125&codeset_id=400614256
@APP.get("/cr-hierarchy")  # maybe junk, or maybe start of a refactor of above
def cr_hierarchy(
    format: str='default',
    codeset_id: Union[str, None] = Query(default=[]),
) -> Dict:

    requested_codeset_ids = parse_codeset_ids(codeset_id)
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)

    lines = []
    def cid_data(cid: int, parent=-1, level=0):
        # fastapi jsonencoder keeps choking on the ints

        rec = {
                  # 'concept_id': int(cid),
                  # 'concept_name': concept_name_lookup[cid],
                  # 'codeset_ids': dsi.codesets_by_concept_id[cid],
                  'level': int(level),
                  # 'parent': int(parent),
                  "ConceptID": ds.concept_name_lookup[cid],
              } | dsi.cset_name_columns
        if format == 'xo':
            rec = {
              "ConceptID": (' -- ' * level) + ds.concept_name_lookup[cid],
            } | dsi.cset_name_columns
        if format == 'flat':
            rec = {
                'concept_id': int(cid),
                'concept_name': ds.concept_name_lookup[cid],
                'level': int(level),
                'codeset_ids': dsi.codesets_by_concept_id[cid] if cid in dsi.codesets_by_concept_id else None,
                  }  # | dsi.cset_name_columns

        return rec

    # TODO: Figure out how to get to return what we need, instead of doing transformation below
    def nested_list(cids: List[int], parent=-1, level=0):
        cids = set(cids)
        for cid in cids:
            d = cid_data(cid, parent, level)
            lines.append(d)
            children: List[int] = dsi.child_cids(cid)
            if children:
    #             print('    ', children)
    #             c = set(children) - cids
                nested_list(children, parent=cid, level=level+1)
    nested_list(dsi.top_level_cids)

    # TODO: Sort related

    result = {'concept_membership': lines, 'csets_info': dsi.csets_info,
              'related_csets': dsi.related.to_dict(orient='records'), }
    return result
    # return json.loads(df.to_json(orient='records'))


@APP.get("/new-hierarchy-stuff")  # maybe junk, or maybe start of a refactor of above
def new_hierarch_stuff(
        format: str='default',
        codeset_id: Union[str, None] = Query(default=[]), ) -> List[Dict]:

    requested_codeset_ids = parse_codeset_ids(codeset_id)
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)




    lines = []
    def cid_data(cid, parent=-1, level=0):
        # fastapi jsonencoder keeps choking on the ints

        rec = {
                  # 'concept_id': int(cid),
                  # 'concept_name': ds.concept_name_lookup[cid],
                  # 'codeset_ids': dsi.codesets_by_concept_id[cid],
                  'level': int(level),
                  # 'parent': int(parent),
                  "ConceptID": ds.concept_name_lookup[cid],
              } | dsi.cset_name_columns
        if format == 'xo':
            rec = {
                      "ConceptID": (' -- ' * level) + ds.concept_name_lookup[cid],
                  } | dsi.cset_name_columns
        if format == 'flat':
            rec = {
                'concept_id': int(cid),
                'concept_name': ds.concept_name_lookup[cid],
                'level': int(level),
                'codeset_ids': dsi.codesets_by_concept_id[cid] if cid in dsi.codesets_by_concept_id else None,
            }  # | dsi.cset_name_columns

        return rec

    def nested_list(cids, parent=-1, level=0):
        cids = set(cids)
        for cid in cids:
            d = cid_data(cid, parent, level)
            lines.append(d)
            children = ds.child_cids(cid)
            if children:
                #             print('    ', children)
                #             c = set(children) - cids
                nested_list(children, parent=cid, level=level+1)

    nested_list(dsi.top_level_cids)
    result = {'lines': lines, 'csets_info': dsi.csets_info, 'related_csets': dsi.related, }
    return result
    # return json.loads(df.to_json(orient='records'))


@APP.get("/concept-sets-with-concepts")
def concept_sets_with_concepts(
    codeset_id: Union[str, None] = Query(default=[]),
) -> Union[Dict, List]:
    """Returns list of concept sets selected and their concepts

    sample url:
        http://127.0.0.1:8000/concept-sets-with-concepts?codeset_id=394464897&codeset_id=13193785

    If no codeset_id, doesn't return concepts; just concept_sets.
        TODO: is that still true?

    Switched to using pandas (not pandasql) not sure if it works like it should -- well
        something's going wrong in json conversion, hitting error when returning. End of
        stacktrace is:
          File "/opt/homebrew/Cellar/python@3.10/3.10.5/Frameworks/Python.framework/Versions/3.10/lib/python3.10/json/encoder.py", line 257, in iterencode
            return _iterencode(o, 0)
        ValueError: Out of range float values are not JSON compliant
    @joeflack4 can you take a look? thanks!
    @siggie: I'm not sure if you still want this, but I coudln't replicate. I added '#pandasql' to a comment below. For
    ...some reason, it said 'table csm not found' when I tried running the sql query.

    """
    # if codeset_id empty, [] otherwise split and convert to int
    codeset_ids = codeset_id and [int(cid) for cid in codeset_id.split('|')] or []

    csm = ds.concept_set_members
    codeset = ds.code_sets

    # TODO #pandasql: switch to using pandasql
    # print(f'Favorite datasets loaded: {DS.keys()}')
    # sql = lambda q: sqldf(q, globals())
    # using pandasql seems to be MUCH slower than regular pandas:
    # csets = sql(f"""
    #     SELECT concept_id
    #     FROM csm
    #     WHERE codeset_id IN (23007370, 23600781)
    # """)

    csm = csm[csm.codeset_id.isin(codeset_ids)]
    codeset = codeset[codeset.codeset_id.isin(codeset_ids)]
    csets = codeset.to_dict(orient='records')
    for cset in csets:
        concept_data: List[Dict] = csm[csm.codeset_id == cset['codeset_id']].to_dict(orient='records')
        cset['concepts'] = {x['concept_id']: x for x in concept_data} if concept_data else {}

    return csets


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
