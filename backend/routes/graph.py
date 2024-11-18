"""Graph related functions and routes"""
import os, warnings
import dateutil.parser as dp
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Set, Tuple, Union, Dict, Optional

import pickle
import networkx as nx
from fastapi import APIRouter, Query, Request
from networkx import DiGraph
from sqlalchemy import Row, RowMapping
from sqlalchemy.sql import text

from backend.routes.db import get_cset_members_items
from backend.db.queries import get_concepts
from backend.db.utils import check_db_status_var, get_db_connection, SCHEMA
from backend.api_logger import Api_logger
from backend.utils import get_timer, commify

VERBOSE = False
PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')
GRAPH_PATH = os.path.join(VOCABS_PATH, 'relationship_graph.pickle')
GRAPH_UNDIRECTED_PATH = os.path.join(VOCABS_PATH, 'relationship_graph_undirected.pickle')

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/concept-graph")
async def concept_graph_get(
    request: Request, codeset_ids: List[int] = Query(...), cids: Optional[List[int]] = Query(None),
    hide_vocabs = ['RxNorm Extension'], hide_nonstandard_concepts=False, verbose = VERBOSE,
) -> Dict[str, Any]:
    """Return concept graph"""
    cids = cids if cids else []
    return await concept_graph_post(request, codeset_ids, cids, hide_vocabs, hide_nonstandard_concepts, verbose)


@router.post("/concept-graph")
async def concept_graph_post(
    request: Request, codeset_ids: List[int], cids: Union[List[int], None] = [],
    hide_vocabs = ['RxNorm Extension'], hide_nonstandard_concepts=False, verbose = VERBOSE,
) -> Dict:
    """Return concept graph via HTTP POST"""
    rpt = Api_logger()
    try:
        await rpt.start_rpt(request, params={'codeset_ids': codeset_ids, 'cids': cids})

        hide_vocabs = hide_vocabs if isinstance(hide_vocabs, list) else []
        sg: DiGraph
        hidden_by_voc: Dict[str, Set[int]]
        nonstandard_concepts_hidden: Set[int]

        sg, concept_ids, hidden_dict, nonstandard_concepts_hidden = await concept_graph(
            codeset_ids, cids, hide_vocabs, hide_nonstandard_concepts, verbose)
        missing_from_graph = set(concept_ids) - set(sg.nodes)

        await rpt.finish(rows=len(sg))
        return {
            'edges': list(sg.edges),
            'concept_ids': concept_ids,
            'missing_from_graph': missing_from_graph,
            'hidden_by_vocab': hidden_dict,
            'nonstandard_concepts_hidden': nonstandard_concepts_hidden}
    except Exception as e:
        await rpt.log_error(e)
        raise e


async def concept_graph(
    codeset_ids: List[int], cids: Union[List[int], None] = [], hide_vocabs = [],
    hide_nonstandard_concepts=False, verbose = VERBOSE, all_descendants = True
 ) -> Tuple[DiGraph, Set[int], Set[int], Dict[str, Set[int]], Set[int]]:
    """Return concept graph

        concepts/concept_ids will include all definition and expansion concepts for codeset_ids
            plus any cids that are passed in
    :returns
      hidden_by_voc: Map of vocab to set of concept ids"""
    timer = get_timer('')
    verbose and timer('concept_graph()')

    # Get concepts & metadata
    concepts_unfiltered: List[RowMapping] = get_cset_members_items(
        codeset_ids=codeset_ids, columns=['concept_id', 'vocabulary_id', 'standard_concept'])
    concepts: List[Dict[str, Any]]
    hidden_by_voc: Dict[str, Set[int]]
    nonstandard_concepts_hidden: Set

    if cids:
        more_concepts = get_concepts(cids)
        concepts_unfiltered.extend(more_concepts)

    # - filter: by vocab & non-standard
    concepts, hidden_by_voc, nonstandard_concepts_hidden = filter_concepts(
        concepts_unfiltered, hide_vocabs, hide_nonstandard_concepts)
    concept_ids: Set[int] = set([c['concept_id'] for c in concepts])
    # concept_ids.update(cids)  # future

    # 2024-10-22. What if we get all descendants, not just missing in between?
    # 2024-11-18. It's been working ok. Now getting rid of all missing-in-between stuff.
    #               Return to commit fdb472ee1bf14156e87c324f2d7297ea2df3601d to get it back.
    more_concept_ids: Set[int] = get_all_descendants(REL_GRAPH, concept_ids)

    # merge and filter
    more_concepts: List[RowMapping] = get_concepts(more_concept_ids)
    concepts_m: List[Dict]
    hidden_by_voc_m: Dict[str, Set[int]]
    nonstandard_concepts_hidden_m: Set
    # - filter more_concepts: by vocab & non-standard
    concepts_m, hidden_by_voc_m, nonstandard_concepts_hidden_m = filter_concepts(
        more_concepts, hide_vocabs, hide_nonstandard_concepts)

    # Merge: more_concepts into concept_ids
    concept_ids.update(more_concept_ids)
    for voc, hidden in hidden_by_voc_m.items():
        hidden_by_voc[voc] = hidden_by_voc.get(voc, set()).union(hidden)
    nonstandard_concepts_hidden = nonstandard_concepts_hidden.union(nonstandard_concepts_hidden_m)

    # Get subgraph
    sg: DiGraph = REL_GRAPH.subgraph(concept_ids)

    # Return
    verbose and timer('done')
    return sg, concept_ids, more_concept_ids, hidden_by_voc, nonstandard_concepts_hidden


def get_all_descendants(g: nx.DiGraph, subgraph_nodes: Union[List[int], Set[int]]) -> Set[int]:
    """Get all descendants of a set of nodes

    Using this instead of get_missing_in_between_nodes. this way the front end has the entire descendant tree for all
    concepts being looked at.
    """
    descendants: Set[int] = set()
    for node in subgraph_nodes:
        if g.has_node(node):
            descendants.update(g.successors(node))
    return descendants


# TODO: @Siggie: move below to frontend
# noinspection PyPep8Naming
def MOVE_TO_FRONT_END():
    """Move to front end"""
    hidden_by_voc = {}
    hide_if_over = 50
    tree = [] # this used to be indented tree stuff that we're no longer using
    # TODO: but I should allow hiding vocabs again (used to be RxNorm Extension only
    #   but now nothing. But vocab hiding, unlike the other stuff that was stashed in
    #   this function, belongs on backend, right?
    for vocab in hidden_by_voc.keys():
        hidden_concept_ids = hidden_by_voc[vocab]
        cnt = len(hidden_concept_ids)
        # noinspection PyTypeChecker
        tree.append((0, f'Concept set also includes {cnt} {vocab} concepts not shown above'))
        if cnt <= hide_if_over:
            for h in hidden_concept_ids:
                tree.append((1, h))


def filter_concepts(
    concepts: List[Union[Dict[str, Any], RowMapping]], hide_vocabs: List[str], hide_nonstandard_concepts=False
) -> Tuple[List[Dict], Dict[str, Set[int]], Set[int]]:
    """Get lists of concepts for graph

    :param: concepts: List of concept ids as keys, and metadata as values.
    :returns
      hidden_by_voc: Map of vocab to set of concept ids"""
    # Hide by vocabulary
    hidden_by_voc: Dict[str, Set[int]] = {}
    for vocab in hide_vocabs:  # for each vocab being hidden, separate out the concepts
        hidden_i: Set[int] = set([c['concept_id'] for c in concepts if c['vocabulary_id'] == vocab])
        if hidden_i:
            hidden_by_voc[vocab] = hidden_i

    # Hide non-standard concepts
    nonstandard_concepts_hidden = set()
    if hide_nonstandard_concepts:
        nonstandard_concepts_hidden: Set[int] = set([c['concept_id'] for c in concepts if c['standard_concept'] != 'S'])

    # Get filtered concepts
    hidden_nodes = set().union(*list(hidden_by_voc.values())).union(nonstandard_concepts_hidden)
    filtered_concepts: List[Dict[str, Any]] = [c for c in concepts if c['concept_id'] not in hidden_nodes]
    return filtered_concepts, hidden_by_voc, nonstandard_concepts_hidden


# print_stack = lambda s: ' | '.join([f"{n} => {','.join([str(x) for x in p])}" for n,p in s])
# print_stack = lambda s: ' | '.join([f"{n} => {str(p)}" for n,p in s])
# print_stack = lambda s: ' | '.join([f"""{n}{'=>' if p else ''}{','.join(p)}""" for n,p in reversed(s)])
print_stack = lambda s: ' | '.join([f"{n} => {','.join([str(x) for x in p])}" for n,p in s])


@router.get("/wholegraph")
def wholegraph():
    """Get subgraph edges for the whole graph"""
    return list(REL_GRAPH.edges)


def condense_super_nodes(sg, threshhold=10):  # todo
    """Condense super nodes"""
    super_nodes = [node for node, degree in sg.out_degree() if degree > threshhold]
    # for node in super_nodes:
    # sg.discard(node) -- n
    return NotImplementedError(super_nodes)


# noinspection PyPep8Naming
def expand_super_node(G, subgraph_nodes, super_node):  # todo
    """Expand super node"""
    # sg = G.subgraph(subgraph_nodes)
    return NotImplementedError(G, subgraph_nodes, super_node)


def from_pydot_layout(g):  # Todo
    """From PyDot layout"""
    return NotImplementedError(g)
# def find_nearest_common_ancestor(G, nodes):
#     all_ancestors = [set(nx.ancestors(G, node)) for node in nodes]
#     common_ancestors = set.intersection(*all_ancestors)
#
#     # Find the lowest common ancestor
#     lowest_common_ancestor = None
#     for ancestor in common_ancestors:
#         if all(ancestor in ancestors or ancestor == node for node, ancestors in zip(nodes, all_ancestors)):
#             if lowest_common_ancestor is None or not ancestor in nx.ancestors(G, lowest_common_ancestor):
#                 lowest_common_ancestor = ancestor
#
#     return lowest_common_ancestor
#
#
# def connect_roots(G, target_nodes):
#     # Find the nearest common ancestor
#     nca = find_nearest_common_ancestor(G, target_nodes)
#
#     # Create a subgraph including the paths from the nearest common ancestor to the target nodes
#     edges_to_include = set()
#     for node in target_nodes:
#         path = nx.shortest_path(G, nca, node)
#         edges_to_include.update([tuple(l) for l in zip(path, path[1:])])
#
#     SG = G.edge_subgraph(edges_to_include).copy()
#     return SG


def generate_graph_edges() -> Iterable[Row]:
    """Generate graph edges"""
    with get_db_connection() as con:
        # moving the sql to ddl-20-concept_graph.jinja.sql

        query = f"""
        SELECT * FROM {SCHEMA}.concept_graph
        """

        result = con.execute(text(query))

        for row in result:
            yield row


# todo: control verbosity?
def create_rel_graphs(save_to_pickle: bool) -> DiGraph:
    """Create relationship graphs"""
    timer = get_timer('create_rel_graphs')

    timer('get edge records')
    edge_generator = generate_graph_edges()

    # noinspection PyPep8Naming
    G = nx.DiGraph()
    if save_to_pickle:
        msg = 'loading and pickling'
        pickle_file = open(GRAPH_PATH, 'ab')
    else:
        msg = 'loading'
        pickle_file = None

    timer(msg)
    rownum = 0
    chunk_size = 10000
    msg = msg.replace('ing', 'ed')
    edges = []
    chunks_loaded = 0
    for source, target in edge_generator:
        edges.append((source, target))
        rownum += 1
        if rownum >= chunk_size:
            chunks_loaded += 1
            G.add_edges_from(edges)
            edges = []
            if chunks_loaded % 100 == 0:
                timer(f'{commify(chunks_loaded * chunk_size)} rows {msg}')
            rownum = 0

    if save_to_pickle:
        timer('saving to pickle')
        pickle.dump(G, pickle_file)  # , pickle.HIGHEST_PROTOCOL

    timer('done')
    return G # , Gu


def is_graph_up_to_date(graph_path: str = GRAPH_PATH) -> bool:
    """Determine if the networkx relationship_graph derived from OMOP vocab is current"""
    voc_last_updated = dp.parse(check_db_status_var('last_refreshed_vocab_tables'))
    graph_last_updated = datetime.fromtimestamp(os.path.getmtime(graph_path))
    if voc_last_updated.tzinfo and not graph_last_updated.tzinfo:  # if one has timezone, both need
        graph_last_updated = graph_last_updated.replace(tzinfo=voc_last_updated.tzinfo)
    return graph_last_updated > voc_last_updated


# noinspection PyPep8Naming for_G
def load_relationship_graph(graph_path: str = GRAPH_PATH, update_if_outdated=True, save=True) -> DiGraph:
    """Load relationship graph from disk"""
    timer = get_timer('./load_relationship_graph')
    timer(f'loading {graph_path}')
    up_to_date = True if not update_if_outdated else is_graph_up_to_date(GRAPH_PATH)
    if os.path.isfile(graph_path) and up_to_date:
        with open(graph_path, 'rb') as pickle_file:
            G: DiGraph = pickle.load(pickle_file)
    else:
        G: DiGraph = create_rel_graphs(save)
    timer('done')
    return G


LOAD_FROM_PICKLE = False
LOAD_RELGRAPH = True

if __name__ == '__main__':
    pass
else:
    # if you don't want graph loaded, then somewhere up in the import tree, do this
    #   import builtins
    #   builtins.DONT_LOAD_GRAPH = True
    import builtins
    if hasattr(builtins, 'DONT_LOAD_GRAPH') and builtins.DONT_LOAD_GRAPH:
        warnings.warn('not loading relationship graph')
    else:
        REL_GRAPH = load_relationship_graph()
