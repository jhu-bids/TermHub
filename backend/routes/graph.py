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
    indented=False  # TODO: if we keep this around, it's annoying that it ends up a string ('true')
) -> Dict[str, Any]:
    """Return concept graph"""
    cids = cids if cids else []
    return await concept_graph_post(
        request, codeset_ids, cids, hide_vocabs, hide_nonstandard_concepts, verbose, indented)


# TODO: match return of concept_graph()
@router.post("/concept-graph")
async def concept_graph_post(
    request: Request, codeset_ids: List[int], cids: Union[List[int], None] = [],
    hide_vocabs = ['RxNorm Extension'], hide_nonstandard_concepts=False, verbose = VERBOSE, indented=False
) -> Union[Dict[str, Any], List[List[Union[int, Any]]]]:
    """Return concept graph

    :returns:  Dict[str, Any] if not indented, else List[List[Union[int, Any]]]"""
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

        if indented:
            # tree = get_indented_tree_nodes(sg, preferred_concept_ids)  # TODO: just testing below, put this line back
            tree: List[List[Union[int, Any]]] = [list(x) for x in get_indented_tree_nodes(sg)]  # TODO: just testing below, put this line back
            return tree

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
    hide_nonstandard_concepts=False, verbose = VERBOSE
 ) -> Tuple[DiGraph, Set[int], Set[int], Dict[str, Set[int]], Set[int]]:
    """Return concept graph

    :param cids: Not used right now. This is for when we allow user to add concepts from other concept sets
    . They're not part of any codesets yet, as these are added by user.
    :returns
      hidden_by_voc: Map of vocab to set of concept ids"""
    if cids:
        raise NotImplementedError('See docstring for concept_graph()')
    # todo: old code to remove. Returns nothing right now. all code below this point in concept_graph_post() used to
    #  be part of get_connected_subgraph() or one of its sub-functions.
    # (nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden_nodes,
    #  hidden_dict) = get_connected_subgraph(REL_GRAPH, codeset_ids, cids, hide_vocabs=['RxNorm Extension'])
    # tree = await indented_concept_list(codeset_ids, cids, hide_vocabs)
    # sg, filled_gaps = fill_in_gaps(REL_GRAPH, id, return_missing=True)
    timer = get_timer('')
    verbose and timer('concept_graph()')

    # Get concepts & metadata
    concepts_unfiltered: List[RowMapping] = get_cset_members_items(
        codeset_ids=codeset_ids, columns=['concept_id', 'vocabulary_id', 'standard_concept'])
    concepts: List[Dict[str, Any]]
    hidden_by_voc: Dict[str, Set[int]]
    nonstandard_concepts_hidden: Set
    # - filter: by vocab & non-standard
    concepts, hidden_by_voc, nonstandard_concepts_hidden = filter_concepts(
        concepts_unfiltered, hide_vocabs, hide_nonstandard_concepts)
    concept_ids: Set[int] = set([c['concept_id'] for c in concepts])
    # concept_ids.update(cids)  # future

    # Fill gaps
    missing_in_betweens_ids: Set[int] = get_missing_in_between_nodes(REL_GRAPH, concept_ids)
    missing_in_betweens: List[RowMapping] = get_concepts(missing_in_betweens_ids)
    concepts_m: List[Dict]
    hidden_by_voc_m: Dict[str, Set[int]]
    nonstandard_concepts_hidden_m: Set
    # - filter missing_in_betweens: by vocab & non-standard
    concepts_m, hidden_by_voc_m, nonstandard_concepts_hidden_m = filter_concepts(
        missing_in_betweens, hide_vocabs, hide_nonstandard_concepts)

    # Merge: missing_in_betweens into concept_ids
    concept_ids.update(missing_in_betweens_ids)
    for voc, hidden in hidden_by_voc_m.items():
        hidden_by_voc[voc] = hidden_by_voc.get(voc, set()).union(hidden)
    nonstandard_concepts_hidden = nonstandard_concepts_hidden.union(nonstandard_concepts_hidden_m)

    # Get subgraph
    sg: DiGraph = REL_GRAPH.subgraph(concept_ids)

    # Return
    verbose and timer('done')
    return sg, concept_ids, missing_in_betweens_ids, hidden_by_voc, nonstandard_concepts_hidden


# TODO: @Siggie: move below to frontend
# noinspection PyPep8Naming
def MOVE_TO_FRONT_END():
    """Graph related code"""
    concept_ids = []
    concepts = []
    sg = nx.DiGraph()
    hidden_by_voc = {}

    # Orphans
    # orphans_not_in_graph, here, are just nodes that don't appear in graph
    #   they'll get appended to the end of the tree at level 0
    # The graph, which comes from the concept_ancestor table, doesn't contain edges for every concept.
    # noinspection PyUnreachableCode
    nodes_in_graph = set()
    orphans_not_in_graph = set()
    # TODO: deal with two kinds of orphan: not in the graph (handled here)
    #   and in the graph but having no parents or children
    for cid in concept_ids:
        if cid in sg.nodes():
            nodes_in_graph.add(cid)
        else:
            orphans_not_in_graph.add(cid)

    # Preferred concept IDs are things we're trying to link in the graph; non-orphan items
    #  - We don't want to accidentally hide them.
    #  - for indented list
    preferred_concept_ids = set([
        c['concept_id'] for c in concepts
        if c['item'] and not c['concept_id'] in orphans_not_in_graph])

    # Layout - no longer used
    # P = to_pydot(sg)
    # layout = from_pydot(P)
    # layout = {k: list(v) for k, v in _layout.items()}     # networkx doesn't seem to have sugiyama
    # g = Graph.from_networkx(sg)
    # _layout = g.layout_sugiyama()
    # layout = {v["_nx_name"]: _layout[idx] for idx, v in enumerate(g.vs)}
    # await rpt.finish(rows=len(tree))
    # return tree

    # Get Concept Set Members Items
    VERBOSE and get_timer('get roots')
    # noinspection PyCallingNonCallable
    roots = [node for node, degree in sg.in_degree() if degree == 0]
    # noinspection PyCallingNonCallable
    leaves = [node for node, degree in sg.out_degree() if degree == 0]

    # orphans_unlinked: nodes that are both root and leaf, put in orphans_unlinked, remove from roots
    #  - in subgraph sg, but not in the connected graph
    # todo: undersrtand what's different between orphans_unlinked and orphans_not_in_graph
    orphans_unlinked = set(roots).intersection(leaves)
    for o in orphans_unlinked:
        roots.remove(o)

    preferred_concept_ids.update(roots)

    # sg_nodes = set(sg.nodes)
    # print(f"sg \u2229 paths {len(sg_nodes.intersection(nodes_in_paths))}")
    # print(f"sg - paths {len(sg_nodes.difference(nodes_in_paths))}")
    # print(f"paths - sg {len(nodes_in_paths.difference(sg_nodes))}")

    VERBOSE and get_timer('get tree')
    # tree = await indented_concept_list(codeset_ids, cids, hide_vocabs)
    tree = get_indented_tree_nodes(sg, preferred_concept_ids)  # TODO: just testing below, put this line back

    hide_if_over = 50
    if orphans_not_in_graph:
        cnt = len(orphans_not_in_graph)
        # noinspection PyTypeChecker
        tree.append((0, f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes in concept"
                        f" set but not in our graph"))
        if cnt <= hide_if_over:
            for orphan in orphans_not_in_graph:
                tree.append((1, orphan))

    if orphans_unlinked:
        cnt = len(orphans_unlinked)
        # noinspection PyTypeChecker
        tree.append((0,
                     f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes unconnected to "
                     f"others in the concept set"))
        if cnt <= hide_if_over:
            for orphan in orphans_unlinked:
                tree.append((1, orphan))

    for vocab in hidden_by_voc.keys():
        hidden_concept_ids = hidden_by_voc[vocab]
        cnt = len(hidden_concept_ids)
        # noinspection PyTypeChecker
        tree.append((0, f'Concept set also includes {cnt} {vocab} concepts not shown above'))
        if cnt <= hide_if_over:
            for h in hidden_concept_ids:
                tree.append((1, h))

    # timer('get testtree')
    # testtree = paths_as_indented_tree(paths)
    # testtree.append((0, list(orphans_not_in_graph)))
    # return testtree
    # noinspection PyTypeChecker
    return tree


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


def get_indented_tree_nodes(
    sg, preferred_concept_ids: Union[List, Set]=[], max_depth=3, max_children=20, small_graph_threshold=2000
) -> List[Tuple[int, int]]:
    """Get indented tree nodes"""
    # noinspection PyShadowingNames
    def dfs(node, depth):
        """Depth-first search"""
        nonlocal tree, small_graph_big_tree, start_over
        if start_over:
            return 'start over'
        tree.append((depth, node))
        preferred_but_unshown.discard(node)

        children = set(sg.successors(node))

        # even if the graph is small, with repetition it can get huge --
        #   so let's start over and respect the max_depth and max_children
        if not small_graph_big_tree and len(sg.nodes) < small_graph_threshold:
            if len(tree) < small_graph_threshold * 2:
                for child in children:
                    if not start_over and dfs(child, depth + 1) == 'start over':
                        start_over = True
                        return 'start over'
                return
            else:
                small_graph_big_tree = True
                return 'start over'

        if len(children) <= max_children and len(children) and depth <= max_depth: # ok to show
            for child in children:
                dfs(child, depth + 1)
        else: # summarize (except always_show)
            always_show = children.intersection(preferred_concept_ids)
            children_to_hide = children.difference(always_show)
            for child in always_show:
                children_to_hide.discard(child)
                dfs(child, depth + 1)
            if children_to_hide:
                tree.append((depth + 1, list(children_to_hide)))

    small_graph_big_tree = False
    while True:
        roots = [n for n in sg.nodes if sg.in_degree(n) == 0]
        tree = []
        preferred_but_unshown = set(preferred_concept_ids)
        start_over = False
        for root in roots:
            if dfs(root, 0) == 'start over':
                start_over = True
                break
        if not start_over:
            break


    for node in preferred_but_unshown:
        tree.append((0, node))

    return tree


# def get_connected_subgraph(REL_GRAPH: nx.Graph, nodes: Set[int]) -> (
#     DiGraph, Set[int], Set[int], Set[int], Dict[str, Set[int]]):
#
#     missing_in_between_nodes = get_missing_in_between_nodes(REL_GRAPH, nodes).copy()
#     # sg = connect_nodesOLD(REL_GRAPH, nodes_in_graph, preferred_concept_ids).copy()
#     return nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden_nodes, hidden_dict


def get_connected_subgraph(
    g: nx.Graph,
    codeset_ids: List[int],
    cids: Union[List[int], None] = [],
    hide_vocabs: Union[List[str], None] = []
) -> (DiGraph, Set[int], Set[int], Set[int], Dict[str, Set[int]]):
    """Get connected subgraph and various other things"""
    print(g, codeset_ids, cids, hide_vocabs)
    raise NotImplementedError('Moved to concept_graph_post()')


print_stack = lambda s: ' | '.join([f"{n} => {','.join([str(x) for x in p])}" for n,p in s])


# noinspection PyPep8Naming
def get_missing_in_between_nodes(G: DiGraph, subgraph_nodes: Union[List[int], Set[int]], verbose=VERBOSE) -> Set:
    """Get missing in-betweens, nodes that weren't in definition or expansion but are in between those."""
    missing_in_between_nodes = set()
    missing_in_between_nodes_tmp = set()
    sg: DiGraph = G.subgraph(subgraph_nodes)
    # noinspection PyCallingNonCallable
    leaves = [node for node, degree in sg.out_degree() if degree == 0]
    visited = set()

    for leaf_node in leaves:
        # stack = [(leaf_node, iter(G.predecessors(leaf_node)))]
        descending_from = None
        stack = [(leaf_node, list(list(G.predecessors(leaf_node))))]

        while stack:
            # if descending_from:
                # if descending_from in subgraph_nodes:
                #     missing_in_between_

            current_node, predecessors = stack[-1]
            if verbose and len(subgraph_nodes) < 1000:
                print(f"{str(print_stack(stack)):58} {(descending_from or ''):8} "
                      f"{','.join([str(n) for n in missing_in_between_nodes])} | "
                      f"{','.join([str(n) for n in missing_in_between_nodes_tmp])}")

            # try:
            # next_node = next(predecessors)
            next_node = predecessors.pop(0) if predecessors else None
            if next_node:
                descending_from = None
                if next_node not in visited:
                    visited.add(next_node)

                    if next_node not in subgraph_nodes:
                        missing_in_between_nodes_tmp.add(next_node)

                    # stack.append((next_node, iter(G.predecessors(next_node))))
                    stack.append((next_node, list(list(G.predecessors(next_node)))))
            else:
                # while True:
                n, preds = stack.pop()
                descending_from = n if n in subgraph_nodes else f"[{n}]"
                if preds:
                    raise RuntimeError("this shouldn't happen")

                if n in subgraph_nodes:
                    missing_in_between_nodes.update(missing_in_between_nodes_tmp)
                    missing_in_between_nodes_tmp.clear()
                    break
                else:
                    missing_in_between_nodes_tmp.discard(n)

            # except StopIteration:
            # except IndexError:

    return missing_in_between_nodes


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
