"""Graph related functions and routes"""
import os, warnings
# import csv
# import io
# import json
from pathlib import Path
from typing import Any, Iterable, List, Set, Tuple, Union, Dict, Optional

import pickle
import networkx as nx
# import pydot
from fastapi import APIRouter, Query, Request
from networkx import DiGraph
from sqlalchemy import Row, RowMapping
from sqlalchemy.sql import text

# from fastapi.responses import JSONResponse
# from fastapi.responses import Response
# from fastapi.encoders import jsonable_encoder
# from collections import OrderedDict
# from igraph import Graph
# from networkx.drawing.nx_pydot import to_pydot, from_pydot

from backend.routes.db import get_cset_members_items
from backend.db.queries import get_concepts
from backend.db.utils import get_db_connection, SCHEMA
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
    return await concept_graph_post(request, codeset_ids, cids, hide_vocabs,
                                    hide_nonstandard_concepts, verbose)


# todo: match return of concept_graph()
@router.post("/concept-graph")
async def concept_graph_post(
    request: Request, codeset_ids: List[int], cids: Union[List[int], None] = [],
    hide_vocabs = ['RxNorm Extension'], hide_nonstandard_concepts=False, verbose = VERBOSE,
) -> List[List[Union[int, Any]]]:

    rpt = Api_logger()
    try:
        await rpt.start_rpt(request, params={'codeset_ids': codeset_ids, 'cids': cids})

        hide_vocabs = hide_vocabs if isinstance(hide_vocabs, list) else []
        sg: DiGraph
        missing_in_betweens: List[Dict[str, Any]]
        hidden_by_voc: Dict[str, Set[int]]
        nonstandard_concepts_hidden: Set[int]

        sg, concept_ids, missing_in_betweens, hidden_dict, nonstandard_concepts_hidden = await concept_graph(
            codeset_ids, cids, hide_vocabs, hide_nonstandard_concepts, verbose)
        missing_from_graph = set(concept_ids) - set(sg.nodes)

        await rpt.finish(rows=len(sg))
        return {
            'edges': list(sg.edges),
            'concept_ids': concept_ids,
            'filled_gaps': missing_in_betweens,
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
    if all_descendants:
        more_concept_ids: Set[int] = get_all_descendants(REL_GRAPH, concept_ids)
    else:
        # Fill gaps
        more_concept_ids: Set[int] = get_missing_in_between_nodes(REL_GRAPH, concept_ids)

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


def get_all_descendants(G: nx.DiGraph, subgraph_nodes: Union[List[int], Set[int]], verbose=VERBOSE) -> Set:
    # using this instead of get_missing_in_between_nodes. this way the front end has the entire
    #   descendant tree for all concepts being looked at
    descendants: Set[int] = set()
    for node in subgraph_nodes:
        if G.has_node(node):
            descendants.update(G.successors(node))
    return descendants


# TODO: @Siggie: move below to frontend
# noinspection PyPep8Naming
def MOVE_TO_FRONT_END():
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


# noinspection PyPep8Naming
def get_missing_in_between_nodes(G: nx.DiGraph, subgraph_nodes: Union[List[int], Set[int]], verbose=VERBOSE) -> Set:
    # not using this anymore
    missing_in_between_nodes = set()
    missing_in_between_nodes_tmp = set()
    subgraph_nodes = set(subgraph_nodes)
    # noinspection PyCallingNonCallable
    leaves = [node for node, degree in G.out_degree() if degree == 0]
    leaves = set(leaves).intersection(subgraph_nodes)
    print(f"subgraph: {subgraph_nodes}, leaves: {leaves}")
    # leaves = sorted([node for node, degree in G.out_degree() if degree == 0])
    discard = set()   # nodes not in subgraph and with no predecessors in subgraph

    for leaf_node in leaves:
        descending_from = None
        stack = [(leaf_node, list(list(G.predecessors(leaf_node))))]

        while stack:
            current_node, predecessors = stack[-1]
            # current node is on the top of the stack
            #   if it has predecessors, the first will be shifted off and pushed to top of the stack
            if verbose and len(subgraph_nodes) < 1000:
                print(
                    f"{str(print_stack(stack)):>59}   " # node => [predecessors] | ... from top to bottom of stack
                    f"{(descending_from or ''):8} "
                    f"<{','.join([str(n) for n in missing_in_between_nodes])}> "  # <missing nodes>
                    f"{{{','.join([str(n) for n in missing_in_between_nodes_tmp])}}} "
                    f"--{','.join([str(n) for n in discard]) if discard else ''}"  # <missing nodes>
                )  # {temp missing nodes}

            next_node = predecessors.pop(0) if predecessors else None
            if next_node:
                descending_from = None
                # ignoring visited is messing stuff up visited node is in the graph, i think
                if next_node not in discard:
                    # visited.add(next_node)

                    if next_node not in subgraph_nodes:
                        missing_in_between_nodes_tmp.add(next_node)

                    stack.append((next_node, list(list(G.predecessors(next_node)))))
            else:
                # while True:
                n, preds = stack.pop()
                # descending_from = n if n in subgraph_nodes else f"[{n}]"
                descending_from = f"<= {n}"
                descending_from += '  ' if n in subgraph_nodes else ' x'
                if preds:
                    raise RuntimeError("this shouldn't happen")

                if n in subgraph_nodes:
                    missing_in_between_nodes.update(missing_in_between_nodes_tmp)
                    subgraph_nodes.update(missing_in_between_nodes_tmp)
                    missing_in_between_nodes_tmp.clear()
                    continue
                    # break
                else:
                    missing_in_between_nodes_tmp.discard(n)
                    discard.add(n)
    return missing_in_between_nodes


def test_get_missing_in_between_nodes(
    whole_graph_edges=None, non_subgraph_nodes=None, expected_missing_in_between_nodes=None, subgraph_nodes=None,
    fail=True, verbose=False
):
    # add code to load whole REL_GRAPH
    G = DiGraph(whole_graph_edges)
    subgraph_nodes = subgraph_nodes or set(G.nodes) - set(non_subgraph_nodes)
    missing_in_between_nodes = get_missing_in_between_nodes(G, subgraph_nodes, verbose=verbose)
    if fail:
        assert missing_in_between_nodes == set(expected_missing_in_between_nodes)
    else:
        if missing_in_between_nodes == set(expected_missing_in_between_nodes):
            print(f"passed with {missing_in_between_nodes}")
        else:
            print(f"expected {expected_missing_in_between_nodes}, got {missing_in_between_nodes}")


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


def load_relationship_graph(save_if_not_exists=True):
    """Load relationship graph from disk"""
    timer = get_timer('./load_relationship_graph')
    timer(f'loading {GRAPH_PATH}')
    if os.path.isfile(GRAPH_PATH):
        with open(GRAPH_PATH, 'rb') as pickle_file:
            # noinspection PyPep8Naming
            G = pickle.load(pickle_file)
            # while True:
            #     try:
            #         chunk = pickle.load(pickle_file)
            #         G.add_edges_from(chunk)
            #     except EOFError:
            #         break  # End of file reached
    else:
        # noinspection PyPep8Naming
        G = create_rel_graphs(save_if_not_exists)
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
        REL_GRAPH = load_relationship_graph(save_if_not_exists=True)
        # REVERSE_GRAPH = REL_GRAPH.reverse()

        # G_ROOTS = set([n for n in REL_GRAPH.nodes if REL_GRAPH.in_degree(n) == 0])
        # def distance_to_root(G, node):
        #     n = node
        #     d = 0
        #     for p in G.predecessors(node):
        #         if n in G_ROOTS:
        #             return d
        #         d += 1
        #         n = p
        #     raise Exception(f"can't find root for {node}")
