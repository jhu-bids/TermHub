import os, warnings
# import json
# import csv
# import io
from pathlib import Path

from typing import Iterable, List, Union, Dict, Optional
from collections import defaultdict
from itertools import combinations

# import networkx
# from igraph import Graph
# import pydot
# from networkx.drawing.nx_pydot import to_pydot, from_pydot

from fastapi import APIRouter, Query, Request
# from fastapi.responses import JSONResponse
# from fastapi.responses import Response
# from fastapi.encoders import jsonable_encoder
# from collections import OrderedDict
import networkx as nx
import pickle

from sqlalchemy import RowMapping
from sqlalchemy.sql import text

from backend.routes.db import get_cset_members_items, get_concepts
from backend.db.utils import sql_query, get_db_connection, SCHEMA, sql_in
from backend.api_logger import Api_logger
from backend.utils import pdump, get_timer, commify, powerset

VERBOSE = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')
GRAPH_PATH = os.path.join(VOCABS_PATH, 'relationship_graph.pickle')
GRAPH_UNDIRECTED_PATH = os.path.join(VOCABS_PATH, 'relationship_graph_undirected.pickle')

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

@router.get("/wholegraph")
def subgraph():
    return list(REL_GRAPH.edges)


async def indented_concept_list(
    codeset_ids: List[int], extra_concept_ids: Union[List[int], None] = [], hide_vocabs = ['RxNorm Extension']
) -> List:
    timer = get_timer('')

    # Get Concept Set Members Items
    VERBOSE and timer('get_connected_subgraph')

    sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden = (
        get_connected_subgraph(REL_GRAPH, codeset_ids, extra_concept_ids, hide_vocabs))

    VERBOSE and timer('get roots')
    # timer('get paths')
    # testsg = REL_GRAPH.subgraph(nodes_in_graph)
    # roots = [node for node, degree in testsg.in_degree() if degree == 0]
    roots = [node for node, degree in sg.in_degree() if degree == 0]
    leaves = [node for node, degree in sg.out_degree() if degree == 0]

    orphans_unlinked = set(roots).intersection(leaves)
    for o in orphans_unlinked:
        roots.remove(o)

    preferred_concept_ids.update(roots)

    # paths = all_paths(sg, roots, leaves)
    # timer('testing stuff')
    #
    # nodes_in_paths = set()
    # for path in paths:
    #     nodes_in_paths.update(path)
    # sg_nodes = set(sg.nodes)
    # print(f"sg \u2229 paths {len(sg_nodes.intersection(nodes_in_paths))}")
    # print(f"sg - paths {len(sg_nodes.difference(nodes_in_paths))}")
    # print(f"paths - sg {len(nodes_in_paths.difference(sg_nodes))}")

    VERBOSE and timer('get tree')
    tree = get_indented_tree_nodes(sg, preferred_concept_ids)  # TODO: just testing below, put this line back

    hide_if_over = 50
    if orphans_not_in_graph:
        cnt = len(orphans_not_in_graph)
        tree.append((0, f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes in concept set but not in our graph"))
        if cnt <= hide_if_over:
            for orphan in orphans_not_in_graph:
                tree.append((1, orphan))

    if orphans_unlinked:
        cnt = len(orphans_unlinked)
        tree.append((0, f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes unconnected to others in the concept set"))
        if cnt <= hide_if_over:
            for orphan in orphans_unlinked:
                tree.append((1, orphan))

    for vocab in hidden.keys():
        hidden_concept_ids = hidden[vocab]
        cnt = len(hidden_concept_ids)
        tree.append((0, f'Concept set also includes {cnt} {vocab} concepts not shown above'))
        if cnt <= hide_if_over:
            for h in hidden_concept_ids:
                tree.append((1, h))

    # timer('get testtree')
    # testtree = paths_as_indented_tree(paths)
    # testtree.append((0, list(orphans_not_in_graph)))
    VERBOSE and timer('done')
    # return testtree
    return tree


def get_connected_subgraph(
    REL_GRAPH: nx.Graph,
    codeset_ids: List[int],
    extra_concept_ids: Union[List[int], None] = [],
    hide_vocabs: Union[List[int], None] = []
) -> nx.Graph:

    _csmi = get_cset_members_items(codeset_ids=codeset_ids)
    # concepts = get_concepts(extra_concept_ids)
    # give hidden rxnorm ext count
    hidden = {}
    csmi = set()
    for vocab in hide_vocabs:
        h = set([c['concept_id'] for c in _csmi if c['vocabulary_id'] == vocab])
        if h:
            hidden[vocab] = h
        csmi.update([c for c in _csmi if c['vocabulary_id'] != vocab])

    # Organize Concept IDs
    timer = get_timer('')
    VERBOSE and timer('organize cids')

    concept_ids = set([c['concept_id'] for c in csmi])
    concept_ids.update(extra_concept_ids)

    # Orphans
    # orphans_not_in_graph, here, are just nodes that don't appear in graph
    #   they'll get appended to the end of the tree at level 0
    # The graph, which comes from the concept_ancestor table, doesn't contain edges for every concept.
    nodes_in_graph = set()
    orphans_not_in_graph = set()
    # TODO: deal with two kinds of orphan: not in the graph (handled here)
    #   and in the graph but having no parents or children
    for cid in concept_ids:
        if cid in REL_GRAPH:
            nodes_in_graph.add(cid)
        else:
            orphans_not_in_graph.add(cid)

    # Preferred concept IDs are things we're trying to link in the graph; non-orphan items
    #  - We don't want to accidentally hide them.
    preferred_concept_ids = set([
        c['concept_id'] for c in csmi
        if c['item'] and not c['concept_id'] in orphans_not_in_graph])

    sg = connect_nodes(REL_GRAPH, nodes_in_graph).copy()
    # sg = connect_nodesOLD(REL_GRAPH, nodes_in_graph, preferred_concept_ids).copy()
    return sg, nodes_in_graph, preferred_concept_ids, orphans_not_in_graph, hidden


@router.get("/indented-concept-list")
async def indented_concept_list_get(request: Request, codeset_ids: List[int] = Query(...),
                                extra_concept_ids: Optional[List[int]] = Query(None)) -> List:

    extra_concept_ids = extra_concept_ids if extra_concept_ids else []
    return await indented_concept_list_post(
        request=request, codeset_ids=codeset_ids, extra_concept_ids=extra_concept_ids)


@router.post("/indented-concept-list")
async def indented_concept_list_post(
    request: Request, codeset_ids: List[int], extra_concept_ids: Union[List[int], None] = [],
    hide_vocabs = ['RxNorm Extension'], verbose = False
) -> List:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={
        'codeset_ids': codeset_ids, 'extra_concept_ids': extra_concept_ids})
    try:
        tree = await indented_concept_list(codeset_ids, extra_concept_ids, hide_vocabs)

        await rpt.finish(rows=len(tree))
        return tree
    except Exception as e:
        await rpt.log_error(e)
        raise e


def connect_nodes(G, nodes):
    """Connects all nodes to the nearest common ancestor.
    TODO: tell users when version is based on old vocab because connections might not be
          there anymore, or might require paths that weren't there when it was created
    """
    timer = get_timer('   ')
    nodes = set(nodes)

    VERBOSE and timer('getting already connected nodes')
    nodes_to_connect = set()  # gets smaller as nodes are connected by ancestors
    nodes_already_connected = set()
    additional_nodes = set()  # nodes that will be added in order to connect nodes_to_connect
    sg = G.subgraph(nodes)
    for node in nodes:
        if sg.in_degree(node) == 0:
            nodes_to_connect.add(node)
        else:
            nodes_already_connected.add(node)

    if len(nodes_to_connect) < 2:
        VERBOSE and timer('done')
        return sg

    # maybe will go faster from smaller to larger. With 50 nodes, it's taking -- probably hours
    # combo_sizes = list(range(len(nodes_to_connect), 1, -1))
    combo_sizes = list(range(2, len(nodes_to_connect)))
    for i, set_size in enumerate(combo_sizes):
        found_ancestors = False # if we don't find common ancestors for all 3-node combos
        #   we don't need to bother with 4-node combos
        VERBOSE and timer(f'getting common ancestor for {set_size} node combos')
        for j, combo in enumerate(combinations(nodes_to_connect, set_size)):
            common_ancestor, path_nodes = get_best_common_ancestor(G, combo)
            if not common_ancestor:
                continue
            found_ancestors = True

            additional_nodes.add(common_ancestor)
            additional_nodes.update(path_nodes)
            nodes_to_connect -= set(combo)
            nodes_to_connect -= path_nodes
            # was broken (commit b0dce49c), getting unneeded ancestors
            # with http://127.0.0.1:8000/indented-concept-list?codeset_ids=1000062292
            # it should have stopped at the following node, but kept going higher
            # if 4239975 in additional_nodes:
            #     pass
            # try http://127.0.0.1:3000/cset-comparison?codeset_ids=1000062292&hierarchySettings=%7B%22collapsePaths%22%3A%7B%224180628%2F134057%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224180628%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224023995%2F134057%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224023995%2F4103183%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F43531056%2F4043346%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F43531056%2F4043346%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%2243531057%2F4185503%2F4043346%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F4185503%2F4043346%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%224180628%2F134057%2F321588%2F4239975%2F321319%22%3Atrue%2C%224180628%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%224023995%2F134057%2F321588%2F4239975%2F321319%22%3Atrue%2C%224023995%2F4103183%2F321588%2F4239975%2F321319%22%3Atrue%7D%2C%22hideZeroCounts%22%3Atrue%7D
            #   to see how it's doing now
        if not found_ancestors:
            break

    all_nodes = nodes.union(additional_nodes)
    VERBOSE and timer(f'getting subgraph for {len(all_nodes)} nodes')
    sg = G.subgraph(all_nodes)
    VERBOSE and timer('done')
    return sg


def connect_nodesOLD(G, target_nodes, preferred_nodes: Iterable[int] = None):
    """Connects all nodes in target_nodes to the nearest common ancestor.

    preferred nodes are the version item nodes
    They should be a subset of target_nodes
    Besides those, only item members not descended from one of those needs
    to be connected, but there shouldn't be any (unless their connection was
    lost in vocabulary updates.)
    TODO: tell users when version is based on old vocab because connections might not be
          there anymore, or might require paths that weren't there when it was created
    """
    timer = get_timer('   ')
    nodes_to_connect = set(preferred_nodes)  # gets smaller as nodes are connected by ancestors
    target_nodes = set(target_nodes)
    if nodes_to_connect.difference(target_nodes):
        raise Exception(f"preferred_nodes should be a subset of target_nodes")

    VERBOSE and timer('getting already connected nodes')
    nodes_already_connected = set()

    for a, b in combinations(nodes_to_connect, 2):
        if a == b:
            continue
        try:
            # if a in nodes_already_connected or b in nodes_already_connected:
            #     continue
            # even better, i think -- https://chat.openai.com/share/3070dc23-cfbe-4192-b374-4461dc8f6977
            #   but then could use that in a better refactor -- not sure preferred_nodes is needed
            #   or unrooted children if other stuff is done right
            if nx.has_path(G, a, b):
                nodes_to_connect.discard(b)
                nodes_already_connected.add(b)
            elif nx.has_path(G, b, a):
                nodes_to_connect.discard(a)
                nodes_already_connected.add(a)
        except nx.NetworkXNoPath:
            continue

    # nodes_connected = set()         #
    additional_nodes = set()  # nodes that will be added in order to connect nodes_to_connect

    # Find nodes that are not connected any nodes_to_connect and add them.
    #   The rest will already be connected when we create the subgraph.
    VERBOSE and timer('getting unrooted children')
    unrooted_children = get_unrooted_children(
        G, nodes_to_connect, target_nodes.difference(nodes_to_connect))
    if (unrooted_children):
        # raise Exception("is this ever happening?")
        # TODO: this does actually happen; add comment here about why
        print(f"wasn't expecting to find unrooted children {str(unrooted_children)}") # except if vocab changes disconnected them from any other nodes
        nodes_to_connect.update(unrooted_children)

    if len(nodes_to_connect) < 2:
        VERBOSE and timer(f'only one ancestor for {len(target_nodes)} nodes')
        sg = G.subgraph(target_nodes)
        VERBOSE and timer('done')
        return sg

    # maybe will go faster from smaller to larger. With 50 nodes, it's taking -- probably hours
    # combo_sizes = list(range(len(nodes_to_connect), 1, -1))
    combo_sizes = list(range(len(nodes_to_connect), 2))
    for i, set_size in enumerate(combo_sizes):
        found_ancestors = False # if we don't find common ancestors for all 3-node combos
                                #   we don't need to bother with 4-node combos
        VERBOSE and timer(f'getting common ancestor for {set_size} node combos')
        for j, combo in enumerate(combinations(nodes_to_connect, set_size)):
            common_ancestor, path_nodes = get_best_common_ancestor(G, combo)
            if not common_ancestor:
                continue
            found_ancestors = True

            # nodes_connected.update(combo)
            additional_nodes.add(common_ancestor)
            additional_nodes.update(path_nodes)

            # was broken (commit b0dce49c), getting unneeded ancestors
            # with http://127.0.0.1:8000/indented-concept-list?codeset_ids=1000062292
            # it should have stopped at the following node, but kept going higher
            # if 4239975 in additional_nodes:
            #     pass
            # try http://127.0.0.1:3000/cset-comparison?codeset_ids=1000062292&hierarchySettings=%7B%22collapsePaths%22%3A%7B%224180628%2F134057%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224180628%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224023995%2F134057%2F321588%2F4239975%2F4124706%22%3Atrue%2C%224023995%2F4103183%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F43531056%2F4043346%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F43531056%2F4043346%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%2243531057%2F4185503%2F4043346%2F440142%2F321588%2F4239975%2F4124706%22%3Atrue%2C%2243531057%2F4185503%2F4043346%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%224180628%2F134057%2F321588%2F4239975%2F321319%22%3Atrue%2C%224180628%2F440142%2F321588%2F4239975%2F321319%22%3Atrue%2C%224023995%2F134057%2F321588%2F4239975%2F321319%22%3Atrue%2C%224023995%2F4103183%2F321588%2F4239975%2F321319%22%3Atrue%7D%2C%22hideZeroCounts%22%3Atrue%7D
            #   to see how it's doing now
            nodes_to_connect -= set(combo)
            nodes_to_connect -= path_nodes

            # if nodes_to_connect.difference(unrooted_children):
            #     # not done yet
            #     if preferred_nodes.difference(nodes_connected):    # sanity check
            #         continue
            #     else:
            #         raise Exception("wasn't expecting that!")
            # else:
            #     if preferred_nodes.difference(nodes_already_connected).difference(nodes_connected):
            #         # sanity check
            #         raise Exception("wasn't expecting that!")
            #     else:
            #         everything_is_connected = True
            # raise Exception("something went wrong in connect_nodes")
        if not found_ancestors:
            break

    all_nodes = target_nodes.union(additional_nodes)
    VERBOSE and timer(f'getting subgraph for {len(all_nodes)} nodes')
    sg = G.subgraph(all_nodes)
    VERBOSE and timer('done')
    return sg


def get_best_common_ancestor(G, nodes):
    all_ancestors = [set(nx.ancestors(G, node)) for node in nodes]
    common_ancestors = set.intersection(*all_ancestors)

    if not common_ancestors:
        return None, None

    # TODO: this will go a lot faster if we keep track of ancestors we've
    #   already found
    # path_nodes = set()
    paths = {}

    # if len(nodes) * len(common_ancestors) < 10000:  # 10000 is arbitrary, but this can get very slow for large csets

    if len(common_ancestors) == 1:
        common_ancestor = common_ancestors.pop()
        for node in nodes:
            path = nx.shortest_path(G, common_ancestor, node)
            return common_ancestor, set(path[1: -1])
            # path_nodes.update(path[1: -1])

    elif len(common_ancestors) > 1:
        max_distances = {}
        for ca in common_ancestors:
            for node in nodes:
                path = nx.shortest_path(G, ca, node)
                paths[ca] = path
                # path_nodes.update(path[1: -1])
                max_distances[ca] = max([len(path) - 1 for tn in nodes])

        min_distance = min(max_distances.values())
        min_distance_ancestors = [node for node, dist in max_distances.items() if dist == min_distance]
        if len(min_distance_ancestors) != 1:
            warnings.warn(f"can't choose best ancestor from {str(min_distance_ancestors)} for {str(nodes)}")

        common_ancestor = min_distance_ancestors[0]
        path = paths[common_ancestor]
        return common_ancestor, set(path[1: -1])

    # else:
    #     raise Exception(f"get_best_ancestor broken for {str(nodes)}")
    # return common_ancestor, path_nodes
    raise Exception(f"get_best_ancestor broken for {str(nodes)}")


def distance_to_root(G, node):
    n = node
    d = 0
    for p in G.predecessors(node):
        if n in G_ROOTS:
            return d
        d += 1
        n = p
    raise Exception(f"can't find root for {node}")


def get_unrooted_children(G, roots, children):
    unrooted = []
    for child in children:
        rooted = False
        for root in roots:
            try:
                if nx.has_path(G, root, child):
                    rooted = True
                    break
            except nx.NetworkXNoPath:
                continue
        if not rooted:
            unrooted.append(child)
    return unrooted


def get_indented_tree_nodes(sg, preferred_concept_ids=[], max_depth=3, max_children=20, small_graph_threshold=2000):

    def dfs(node, depth):
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


# test code for the above:
# G = nx.DiGraph([('a','b'), ('a','c'), ('b','d'), ('b','e'), ('c','f'), ('2', 'c'), ('1', '2'), ('1', 'a')])
# target_nodes = ['d', 'e', 'f']
# assert connect_roots(G, target_nodes).edges == nx.DiGraph([('a','b'), ('a','c'), ('b','d'), ('b','e'), ('c','f')]).edges
# print(list(connect_roots(G, target_nodes).edges))

# test tree paths:
# G = nx.DiGraph([('a','b'), ('a','c'), ('b','d'), ('b','e'), ('c','f'), ('2', 'c'), ('1', '2'), ('1', 'a')])
# sg = G.subgraph(['a', 'b', 'c', 'd', 'e', 'f', '1', '2'])
# assert set(sg.edges) == set([('a','b'), ('a','c'), ('b','d'), ('b','e'), ('c','f'), ('2', 'c'), ('1', '2'), ('1', 'a')])
# assert tree_paths = get_indented_tree_nodes(sg) == [ (0, '1'), (1, '2'), (2, 'c'), (3, 'f'), (1, 'a'), (2, 'b'), (3, 'd'), (3, 'e'), (2, 'c'), (3, 'f'), (3, 'c') ]
# assert print_tree_paths(tree_paths) == """
# 1
#     2
#         c
#             f
#     a
#         b
#             d
#             e
#         c
#             f
# """


def condense_super_nodes(sg, threshhold=10):
    super_nodes = [node for node, degree in sg.out_degree() if degree > threshhold]
    # for node in super_nodes:
    # sg.discard(node) -- n

def expand_super_node(G, subgraph_nodes, super_node):
    sg = G.subgraph(subgraph_nodes)


@router.get("/concept-graph")
async def concept_graph(
    request: Request,
    codeset_ids: List[int] = [],
    id: List[int] = Query(...)   # id is a list of concept ids
):
    return await concept_graph_post(request=request, codeset_ids=codeset_ids, concept_ids=id)


@router.post("/concept-graph")
async def concept_graph_post(
    request: Request,
    codeset_ids: List[int] = [],
    concept_ids: List[int] = [],
) -> Dict:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'concept_ids': codeset_ids})

    try:
        # sg, filled_gaps = fill_in_gaps(REL_GRAPH, id, return_missing=True)
        (sg, nodes_in_graph, preferred_concept_ids,
         orphans_not_in_graph, hidden) = get_connected_subgraph(
            REL_GRAPH, codeset_ids, concept_ids, hide_vocabs=['RxNorm Extension'])
        filled_gaps = set(sg.nodes).difference(codeset_ids)
        layout = 'not implemented'
        # raise Exception("Not implemented")
        # P = to_pydot(sg)
        # layout = from_pydot(P)
        # layout = {k: list(v) for k, v in _layout.items()}     # networkx doesn't seem to have sugiyama
        # g = Graph.from_networkx(sg)
        # _layout = g.layout_sugiyama()
        # layout = {v["_nx_name"]: _layout[idx] for idx, v in enumerate(g.vs)}
        await rpt.finish(rows=len(sg))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return {'edges': list(sg.edges), 'layout': layout, 'filled_gaps': filled_gaps}


# def fill_in_gaps(G, codeset_ids, return_missing=False):
#     (sg, nodes_in_graph, preferred_concept_ids,
#      orphans_not_in_graph) = get_connected_subgraph(
#         REL_GRAPH, codeset_ids, hide_vocabs=['RxNorm Extension'])
#     return sg, set(sg.nodes).difference(codeset_ids)
#             #nodes_in_graph, preferred_concept_ids, orphans_not)
#     # sg = G.subgraph(nodes)
#     # roots = [node for node, degree in sg.in_degree() if degree == 0]
#     # leaves = [node for node, degree in sg.out_degree() if degree == 0]
#     # missing_nodes = set()  # nodes needed to traverse all paths but not present in nodes list
#     # for root in roots:
#     #     for leaf in leaves:
#     #         _paths = list(nx.all_simple_paths(G, root, leaf))
#     #         for path in _paths:
#     #             for node in path:
#     #                 if node not in nodes:
#     #                     missing_nodes.add(node)
#     # sgc = G.subgraph(nodes + list(missing_nodes))
#     # if return_missing:
#     #     return sgc, missing_nodes
#     # return sgc


def from_pydot_layout(g):
    pass
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



# def get_paths_to_roots(G, node):
#     # find all paths from a node to all its root nodes
#     paths = []
#     for parent in G.predecessors(node):
#         paths.append(nx.shortest_path(G, parent, node))
#
#     shortest_path = min(paths, key=len)
#     return shortest_path
#
#
# def print_tree_paths(paths):
#     for depth, node in paths:
#         indent = "    " * depth
#         print(f"{indent}{node}")
#
# def all_paths(g: networkx.DiGraph, roots: List[int], leaves: List[int]) -> List[List[int]]:
#     """
#     TODO:   something. this is working better than new technique, but much slower I think
#             i need to compare it with current method to see what went wrong, or if i need
#             this again
#     Creates a subgraph from g using nodes.
#     Identifies root and leaf nodes in this subgraph.
#     Generates all simple paths from each root to each leaf in the original graph g.
#     Returns the list of all such paths.
#     """
#     nodes = set(roots + leaves)
#     paths = []
#     missing_nodes = set()  # nodes needed to traverse all paths but not present in nodes list
#     paths_with_missing_nodes = []
#     descendants_of_missing = set()
#     paths_node_is_in = defaultdict(list)
#     for root in roots:
#         for leaf in leaves:
#             _paths = list(nx.all_simple_paths(g, root, leaf))
#             for path in _paths:
#                 # if len(path) > 1: # do i need this? don't think so; it might hide solitary nodes
#                 paths.append(path)
#                 for node in path:
#                     if path not in paths_node_is_in[node]:
#                         paths_node_is_in[node].append(path)
#                     if node not in nodes:
#                         missing_nodes.add(node)
#                         if not path in paths_with_missing_nodes:
#                             paths_with_missing_nodes.append(path)
#                             for d in path[path.index(node) + 1:]:
#                                 descendants_of_missing.add(d)
#
#     # if a path contains a missing node and all its descendants
#     #   show up in other paths, the path is not needed
#     # especially because we're now including stuff from concept_relationship
#     #   that wouldn't appear in the expansion, ....
#     #   TODO: figure out if the concept_relationship edges are really needed
#
#     # TODO: test that this code is doing what it should (and code above too, while you're at it)
#     descendants_of_missing = descendants_of_missing.difference(missing_nodes)   # in case missing have missing descendants
#
#     for path_with_missing in paths_with_missing_nodes:
#         # for each path with missing nodes, check if their descendants show up in other paths
#         nodes_to_check = set(path_with_missing).intersection(descendants_of_missing)
#         # we have to make sure that every descendant node in this path appears in other paths
#         nodes_not_elsewhere = []
#         for node in nodes_to_check:
#             if not [p for p in paths_node_is_in[node] if p not in paths_with_missing_nodes]:
#                 # this node does not appear in any non-missing-node paths
#                 nodes_not_elsewhere.append(node)
#                 break;
#         if not nodes_not_elsewhere:
#             # every node appears elsewhere; safe to remove
#             paths.discard(path_with_missing)
#
#     return paths
# # def all_paths(g: networkx.DiGraph, nodes: set, preferred_nodes: set = set()) -> List[List[int]]:
# #     """
# #     Creates a subgraph from g using nodes.
# #     Fills in gaps (connect_nodes)
# #     Identifies root and leaf nodes in this subgraph.
# #     Generates all simple paths from each root to each leaf in the original graph g.
# #     Returns the list of all such paths.
# #     """
# #     # sg = g.subgraph(nodes)    # this way give a view of g, which is frozen
# #     # sg = nx.DiGraph(g.subgraph(nodes)) #.copy())  # Creates an independent copy of the subgraph
# #     sg = g.subgraph(nodes).copy()  # Creates an independent copy of the subgraph
# #
# #     nodes = set(nodes)
# #     sg = connect_nodes(g, nodes, preferred_nodes)
# #     paths = get_indented_tree_nodes(sg)
# #     return paths
# #     pass
# #     r = json.dumps(paths)
# #     return r
# #     # roots = [node for node, degree in sg.in_degree() if degree == 0]
# #     # leaves = [node for node, degree in sg.out_degree() if degree == 0]
# #     #
# #     # paths = []
# #     # paths_node_is_in = defaultdict(list)
# #     # # already filling in missing in connect_nodes, so no need to do it here anymore
# #     # # missing_nodes = set()  # nodes needed to traverse all paths but not present in nodes list
# #     # # all_nodes = set(nodes)
# #     # # paths_with_missing_nodes = []
# #     # # descendants_of_missing = set()
# #     # for root in roots:
# #     #     for leaf in leaves:
# #     #         # TODO: fix here, it can get really slow, like with http://127.0.0.1:8000/indented-concept-list?codeset_ids=417730759&codeset_ids=423850600&codeset_ids=966671711&codeset_ids=577774492
# #     #         _paths = list(nx.all_simple_paths(sg, root, leaf))
# #     #         for path in _paths:
# #     #             # if len(path) > 1: # do i need this? don't think so; it might hide solitary nodes
# #     #             paths.append(path)
# #     #             for node in path:
# #     #                 if path not in paths_node_is_in[node]:
# #     #                     paths_node_is_in[node].append(path)
# #     #                 # if node not in nodes:
# #     #                 #     missing_nodes.add(node)
# #     #                 #     all_nodes.add(node)
# #     #                 #     if not path in paths_with_missing_nodes:
# #     #                 #         paths_with_missing_nodes.append(path)
# #     #                 #         for d in path[path.index(node) + 1:]:
# #     #                 #             descendants_of_missing.add(d)
# #     # return paths
#
#
# def paths_as_indented_tree(paths: List[List[int]]) -> List[Tuple[int, int]]:
#     """
#     paths: A list of paths (each path is a list of node identifiers).
#     Initializes a root TreeNode with None value.
#     Inserts each path into this tree.
#     Generates a list of lines where each line represents a level and a node identifier in the indented tree.
#     """
#     # Initialize tree and insert paths
#     root = TreeNode(None)  # Root node doesn't hold any data
#     # paths = [("A", "B", "C"), ("A", "B", "D"), ("E", "B", "C"), ("E", "B", "D")]
#     for path in paths:
#         root.insert(path)
#
#     tree = []
#     for line in generate_indented_nodes(root):
#         # tree.append({'level': line[0], 'concept_id': line[1]})
#         tree.append((line[0], line[1]))
#
#     return tree
#
#
# def generate_indented_nodes(node, level=-1):
#     if node.value is not None:  # Skip the root node
#         yield level, node.value
#     for child in node.children.values():
#         yield from generate_indented_nodes(child, level + 1)
#
#
# class TreeNode:
#     """TODO: document how this works, what it's for (got it from chatgpt)"""
#     """
#     Purpose: Represents a node in the tree, used to construct the indented tree structure.
#     Attributes:
#     value: The value (or identifier) of the node.
#     children: A dictionary of child nodes.
#     Methods:
#     __init__(self, value): Constructor to initialize the node with a value.
#     insert(self, path): Inserts a path into the tree, starting from this node.
#     """
#     def __init__(self, value):
#         self.value = value
#         self.children = {}
#
#     # this was working until i tried having lists for values (so when the tree got too deep
#     #   or the parent node had too many children, it would just give a list of the children
#     #   instead of recursing down into them)
#     def insert(self, path):
#         if path:
#             head, *tail = path
#             if head not in self.children:
#                 self.children[head] = TreeNode(head)
#             self.children[head].insert(tail)
#     # but, also, although this code was working, the variable names are wrong. it assumes
#     #   the path will have a "head" -- which for us is just the indent depth -- and further
#     #   values in the tails, but we only have one value remaining, the node (or, now list of
#     #   nodes) appearing at that spot in the tree
#

def generate_graph_edges():
    with get_db_connection() as con:
        # moving the sql to ddl-20-concept_graph.jinja.sql

        query = f"""
        SELECT * FROM {SCHEMA}.concept_graph
        """

        result = con.execute(text(query))

        for row in result:
            yield row


def create_rel_graphs(save_to_pickle: bool):
    timer = get_timer('create_rel_graphs')

    timer('get edge records')
    edge_generator = generate_graph_edges()

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
    timer = get_timer('./load_relationship_graph')
    timer(f'loading {GRAPH_PATH}')
    if os.path.isfile(GRAPH_PATH):
        G = nx.DiGraph()
        with open(GRAPH_PATH, 'rb') as pickle_file:
            G = pickle.load(pickle_file)
            # while True:
            #     try:
            #         chunk = pickle.load(pickle_file)
            #         G.add_edges_from(chunk)
            #     except EOFError:
            #         break  # End of file reached
    else:
        G = create_rel_graphs(save_if_not_exists)
    timer('done')
    return G


LOAD_FROM_PICKLE = False
LOAD_RELGRAPH = True

if __name__ == '__main__':
    pass
    # create_rel_graphs(save_to_pickle=True)
    # G = for_testing()
    # sg = G.subgraph(1,9)
    # G, components = disconnected_subgraphs()
    # sg = connected_subgraph_from_nodes(G, [3, 7, 12])
    # j = graph_to_json(sg)
    # pdump(j)
else:

    # if you don't want graph loaded, then somewhere up in the import tree, do this
    #   import builtins
    #   builtins.DONT_LOAD_GRAPH = True
    import builtins

    if hasattr(builtins, 'DONT_LOAD_GRAPH') and builtins.DONT_LOAD_GRAPH:
        warnings.warn('not loading relationship graph')
    else:
        REL_GRAPH = load_relationship_graph(save_if_not_exists=True)
        G_ROOTS = set([n for n in REL_GRAPH.nodes if REL_GRAPH.in_degree(n) == 0])

    # The resason this exists below is because we were not sure if, when a variable is imported by multiple files, the
    # code gets run multiple times.
    # if CONFIG['importer'] == 'app.py':
    #     # REL_GRAPH, REL_GRAPH_UNDIRECTED = load_relationship_graph(save_if_not_exists=True)
    #     REL_GRAPH = load_relationship_graph(save_if_not_exists=True)
    # else:
    #     print(f"Imported from {CONFIG['importer']}, not loading relationship graphs")
