"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import json
import os
from pathlib import Path
from subprocess import call as sp_call
from typing import Any, Dict, List, Union, Callable, Set

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
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

    # Filters out any concepts w/ no name
    ds.concept_set_members = ds.concept_set_members[ds.concept_set_members.concept_set_name.str.len() > 0]
    # TODO: try this later. will require filtering other stuff also? This will be useful for provenance
    # ds.concept_set_members = ds.concept_set_members[~ds.concept_set_members.archived]
    # ds.data_messages = [
    #     'concept_set_members filtered to exclude concept sets with empty names'
    #     'concept_set_members filtered to exclude archived concept set'
    # ]

    ds.concept.set_index('concept_id', inplace=True)

    # Reassign; we only care about the subsumes_only
    # ds.subsumes = ds.concept_relationship[ds.concept_relationship.relationship_id == 'Subsumes']
    ds.concept_relationship = ds.concept_relationship_subsumes_only
    ds.links = ds.concept_relationship.groupby('concept_id_1')
    # ds.all_concept_relationship_cids = set(ds.concept_relationship.concept_id_1).union(set(ds.concept_relationship.concept_id_2))

    def child_cids(cid):
        """Return list of `concept_id_2` for each `concept_id_1` (aka all its children)"""
        if cid in ds.links.groups.keys():
            return [int(c) for c in ds.links.get_group(cid).concept_id_2.unique() if c != cid]
    ds.child_cids = child_cids

    def connect_children(pcid, cids):  # how to declare this should be tuple of int or None and list of ints
        if not cids:
            return None
        pcid in cids and cids.remove(pcid)
        pcid_kids = {int(cid): child_cids(cid) for cid in cids}
        # pdump({'kids': pcid_kids})
        return {cid: connect_children(cid, kids) for cid, kids in pcid_kids.items()}

    ds.connect_children = connect_children

    # Take codesets, and merge on container. Add to each version.
    # Some columns in codeset and container have the same name, hence suffix
    # ...The merge on `concept_set_members` is used for concept counts for each codeset version.
    ds.all_csets = ds.code_sets.merge(
        ds.concept_set_container, suffixes=['_version', '_container'], on='concept_set_name').merge(
        ds.concept_set_members.groupby('codeset_id')['concept_id'].nunique().reset_index().rename(
            columns={'concept_id': 'concepts'}), on='codeset_id')

    print('Done building global ds objects')
    return ds

# todo: consider: run 2 backend servers, 1 to hold the data and 1 to service requests / logic? probably.
# TODO: #2: remove try/except when git lfs fully set up
try:
    # todo: temp until we decide if this is the correct way

    # dataset_names = list(FAVORITE_DATASETS.keys()) + ['concept_relationship_is_a']

    dataset_names = ['concept_set_members',
                     'concept',
                     'concept_relationship_subsumes_only',
                     'concept_set_container',
                     'code_sets',
                     'concept_set_version_item']

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
except Exception as err:
    print(f'failed loading datasets', err)

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

    dsi.code_sets_i = ds.code_sets[ds.code_sets['codeset_id'].isin(codeset_ids)]

    dsi.concept_set_members_i = ds.concept_set_members[ds.concept_set_members['codeset_id'].isin(codeset_ids)]

    dsi.concept_relationship_i = ds.concept_relationship[
        (ds.concept_relationship.concept_id_1.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_2.isin(dsi.concept_set_members_i.concept_id)) &
        (ds.concept_relationship.concept_id_1 != ds.concept_relationship.concept_id_2)
        # & (ds.concept_relationship.relationship_id == 'Subsumes')
        ]

    all_csets = ds.all_csets[[
        'codeset_id', 'concept_set_version_title', 'is_most_recent_version', 'intention_version', 'intention_container',
        'limitations', 'issues', 'update_message', 'has_review', 'provenance', 'authoritative_source', 'project_id',
        'status_version', 'status_container', 'stage', 'archived', 'concepts']]

    all_csets['selected'] = all_csets['codeset_id'].isin(codeset_ids)

    # Get related codeset IDs
    concept_ids: Set[int] = set(dsi.concept_set_members_i.concept_id.unique())
    dsi.related_codeset_ids = ds.concept_set_members[
        ds.concept_set_members.concept_id.isin(concept_ids)].codeset_id.unique()
    all_csets['related'] = all_csets['codeset_id'].isin(dsi.related_codeset_ids)

    # Drop duplicates & sort
    all_csets = all_csets.drop_duplicates().sort_values(by=['selected', 'concepts'], ascending=False)

    # Add columns for % overlap: 1) % of selected csets' concepts and 2) % of related cset's concepts
    dsi.concept_set_members_r = ds.concept_set_members[
        ds.concept_set_members['codeset_id'].isin(dsi.related_codeset_ids)
        ].drop_duplicates()

    g = dsi.concept_set_members_r.groupby('codeset_id')
    r_with_intersecting_cids = g.apply(lambda r: set(r.concept_id).intersection(concept_ids))
    if len(r_with_intersecting_cids):
        x = pd.DataFrame(data={'intersecting_concept_ids': r_with_intersecting_cids,})
        x['intersecting_concepts'] = x.intersecting_concept_ids.apply(lambda r: len(r))
        x.drop('intersecting_concept_ids', axis=1, inplace=True)
        all_csets = all_csets.merge(x, how='left', on='codeset_id')
        all_csets = all_csets.convert_dtypes({'intersecting_concepts': 'int'})
        all_csets['recall'] = all_csets.intersecting_concepts / len(concept_ids)
        all_csets['precision'] = all_csets.intersecting_concepts / all_csets.concepts

    dsi.all_csets = all_csets

    # Get relationships for selected code sets
    dsi.links = dsi.concept_relationship_i.groupby('concept_id_1')

    # Get child `concept_id`s
    def child_cids(cid):
        """Closure for geting child concept IDs"""
        if cid in dsi.links.groups.keys():
            return [int(c) for c in dsi.links.get_group(cid).concept_id_2.unique() if c != cid]
    dsi.child_cids = child_cids

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

    return dsi

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

    requested_codeset_ids = parse_codeset_ids(codeset_id)
    # A namespace (like `ds`) specifically for these codeset IDs.
    dsi = data_stuff_for_codeset_ids(requested_codeset_ids)

    c = dsi.connect_children(-1, dsi.top_level_cids)

    result = {
              # 'related_csets': dsi.related.to_dict(orient='records'),
              'concept_set_members_i': json.loads(dsi.concept_set_members_i.to_json(orient='records')),
              'all_csets': json.loads(dsi.all_csets.to_json(orient='records')),
              'hierarchy': c,
              }

    return result


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


# TODO
#  - example case: http://localhost:8000/update-cset-concept-inclusion?codeset_id=496860542&concept_ids=35787839&concept_ids=35787840
#  - old example case pre param change: http://localhost:8000/update-cset-concept-inclusion?codeset_id=496860542&concept_ids=35787839&state=false
# TODO: frontend change
#  We should change this to `concept_ids`: When a box is checked/unchecked, send frontend should send *all* the concept_ids to be included
@APP.get("/update-cset-concept-inclusion")
def update_cset(codeset_id: int, concept_ids: Union[List[int], None] = Query(default=None)) -> Dict:
    modification = {'codeset_id': codeset_id, 'concept_ids': concept_ids}
    print(f'update-cset-concept-inclusion: {codeset_id}: {concept_ids}')
    # TODO: enclave_wrangler: Before doing this, need enclave_wrangler to save files w/ last git hash at time that it last did a download/transform
    #  TODO: uploads/cset_upload_registry
    #    - internal_id: a new id: max(df['internal_id']) + 1
    #    ...source_id_type,source_id,source_id_field,oid,ccsr_code,internal_source,cset_source,grouped_by_bids,concept_id,codeset_id,enclave_codeset_id,enclave_codeset_id_updated_at,concept_set_name
    pass  # todo: read this file, get a new internal_id, and write a new row

    #  TODO: code_sets
    #    - codeset_id: get from uploads/cset_upload_registry.internal_id
    #    - concept_set_version_title: add new row: <name> (v#) --> <name> (draft)
    #    ...project,concept_set_name,source_application,source_application_version,created_at,atlas_json,is_most_recent_version,version,comments,intention,limitations,issues,update_message,status,has_review,reviewed_by,created_by,provenance,atlas_json_resource_url,parent_version_id,authoritative_source,is_draft
    pass  # todo: Could I speed this up by, rather than (a) pandas read/write, (b) open file with python in 'append' mode and add a CSV row. Maybe use csv.writer or just serialize and hope no commas in label, or wrap in "" if comma present?

    #  TODO: concept_set_container
    #    - concept_set_id: this should be same as code_sets.concept_set_version_title
    #    ...project_id,assigned_informatician,assigned_sme,status,stage,intention,n3c_reviewer,alias,archived,concept_set_name,created_by,created_at
    pass

    #  TODO: concept_set_version_item (multiple rows)
    #    - codeset_id: get from uploads/cset_upload_registry.internal_id
    #    - concept_id: Need multiple concept_ids from UI. One row for each. Shouldn't need to look at the concepts that were included in the previous version.
    #    ...item_id,isExcluded,includeDescendants,includeMapped,annotation,created_by,created_at
    pass

    #  TODO: concept_set_members (multiple rows)
    #    (X: do i need this one? will this get automatically updated when we upload to enclave and re-download?
    #    - codeset_id: get from uploads/cset_upload_registry.internal_id
    #    - concept_id: see 'concept_set_version_item.concept_id' notes
    #    ...concept_set_name,is_most_recent_version,version,concept_name,archived
    pass

    # TODO: csets_update() doesn't meet exact needs. not actually updating to an existing index. adding a new row.
    #  - soution: can set index to -1, perhaps, to indicate that it is a new row
    #  - edge case: do i need to worry about multiple drafts at this point? delete if one exists? keep multiple? or at upload time
    #    ...should we update latest and delete excess drafts if exist?
    pass

    # TODO: call the function i defined for updating local git stuff. persist these changes and patch etc
    #     dataset_path: File path. Relative to `/termhub-csets/datasets/`
    #     row_index_data_map: Keys are integers of row indices in the dataset. Values are dictionaries, where keys are the
    #       name of the fields to be updated, and values contain the values to update in that particular cell."""
    # TODO: git/patch changes (do this inside csets_update()): https://github.com/jhu-bids/TermHub/issues/165#issuecomment-1276557733
    result = csets_update(dataset_path='', row_index_data_map={})

    # TODO: Then push to enclave?
    pass

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


# TODO: git/patch changes: https://github.com/jhu-bids/TermHub/issues/165#issuecomment-1276557733
def csets_update(dataset_path: str, row_index_data_map: Dict[int, Dict[str, Any]]) -> Dict:
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
    path = os.path.join(path_root, dataset_path)
    # noinspection PyBroadException
    try:
        df = pd.read_csv(path, dtype={'id': np.int32, 'last_name': str, 'first_name': str}).fillna('')
        for index, field_values in row_index_data_map.items():
            for field, value in field_values.items():
                df.at[index, field] = value
        df.to_csv(path, index=False)
    except BaseException as err:
        result = 'failure'
        details = str(err)

    # Push commit
    # todo?: Correct git status after change should show something like this near end: `modified: FILENAME`
    relative_path = os.path.join('datasets', dataset_path)
    # todo: Want to see result as string? only getting int: 1 / 0
    #  ...answer: it's being printed to stderr and stdout. I remember there's some way to pipe and capture if needed
    # TODO: What if the update resulted in no changes? e.g. changed values were same?
    git_add_result = sp_call(f'git add {relative_path}'.split(), cwd=cset_dir)
    if git_add_result != 0:
        result = 'failure'
        details = f'Error: Git add: {dataset_path}'
    git_commit_result = sp_call(['git', 'commit', '-m', f'Updated by server: {relative_path}'], cwd=cset_dir)
    if git_commit_result != 0:
        result = 'failure'
        details = f'Error: Git commit: {dataset_path}'
    git_push_result = sp_call('git push origin HEAD:main'.split(), cwd=cset_dir)
    if git_push_result != 0:
        result = 'failure'
        details = f'Error: Git push: {dataset_path}'

    return {'result': result, 'details': details}


# TODO: Maybe change to `id` instead of row index
@APP.put("/datasets/csets")
def put_csets_update(d: CsetsUpdate = None) -> Dict:
    """HTTP PUT wrapper for csets_update()"""
    return csets_update(d.dataset_path, d.row_index_data_map)


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


def pdump(o):
    print(json.dumps(o, indent=2))


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


if __name__ == '__main__':
    run()
