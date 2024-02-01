import os, warnings
# import json
# import csv
# import io
from pathlib import Path

from typing import Any, Iterable, List, Set, Union, Dict, Optional
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

from networkx import DiGraph
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


@router.get("/concept-graph")
async def concept_graph(request: Request, codeset_ids: List[int] = Query(...),
                        extra_concept_ids: Optional[List[int]] = Query(None)) -> List:
    extra_concept_ids = extra_concept_ids if extra_concept_ids else []
    return await concept_graph_post(
        request=request, codeset_ids=codeset_ids, extra_concept_ids=extra_concept_ids)


@router.post("/concept-graph")
async def concept_graph_post(
    request: Request, codeset_ids: List[int], extra_concept_ids: Union[List[int], None] = [],
    hide_vocabs = ['RxNorm Extension'], verbose = False
) -> List:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={
        'codeset_ids': codeset_ids, 'extra_concept_ids': extra_concept_ids})
    try:
        timer = get_timer('')
        # tree = await indented_concept_list(codeset_ids, extra_concept_ids, hide_vocabs)
        # sg, filled_gaps = fill_in_gaps(REL_GRAPH, id, return_missing=True)
        VERBOSE and timer('get_connected_subgraph')
        # VERBOSE and timer('get_missing_in_between_nodes')
        (nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden_nodes,
         hidden_dict) = get_connected_subgraph(REL_GRAPH, codeset_ids, extra_concept_ids,
                                               hide_vocabs=['RxNorm Extension'])


        # Organize Concept IDs
        timer = get_timer('')
        VERBOSE and timer('organize cids')

        concepts, hidden_dict = get_concepts_for_graph(codeset_ids, extra_concept_ids, hide_vocabs)
        concept_ids = set([c['concept_id'] for c in concepts])
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

        missing_in_between_nodes = get_missing_in_between_nodes(REL_GRAPH, nodes_in_graph).copy()
        # sg = connect_nodesOLD(REL_GRAPH, nodes_in_graph, preferred_concept_ids).copy()
        return nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden_nodes, hidden_dict

        sg = REL_GRAPH.subgraph(nodes_in_graph.union(missing_in_between_nodes))
        layout = 'not implemented'
        # raise Exception("Not implemented")
        # P = to_pydot(sg)
        # layout = from_pydot(P)
        # layout = {k: list(v) for k, v in _layout.items()}     # networkx doesn't seem to have sugiyama
        # g = Graph.from_networkx(sg)
        # _layout = g.layout_sugiyama()
        # layout = {v["_nx_name"]: _layout[idx] for idx, v in enumerate(g.vs)}
        # await rpt.finish(rows=len(tree))
        # return tree
        # Get Concept Set Members Items

        VERBOSE and timer('get roots')
        roots = [node for node, degree in sg.in_degree() if degree == 0]
        leaves = [node for node, degree in sg.out_degree() if degree == 0]

        # nodes that are both root and leaf, put in orphans_unlinked, remove from roots
        orphans_unlinked = set(roots).intersection(leaves)
        for o in orphans_unlinked:
            roots.remove(o)

        preferred_concept_ids.update(roots)

        # sg_nodes = set(sg.nodes)
        # print(f"sg \u2229 paths {len(sg_nodes.intersection(nodes_in_paths))}")
        # print(f"sg - paths {len(sg_nodes.difference(nodes_in_paths))}")
        # print(f"paths - sg {len(nodes_in_paths.difference(sg_nodes))}")

        VERBOSE and timer('get tree')
        tree = get_indented_tree_nodes(sg, preferred_concept_ids)  # TODO: just testing below, put this line back

        hide_if_over = 50
        if orphans_not_in_graph:
            cnt = len(orphans_not_in_graph)
            tree.append((0,
                         f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes in concept set but not in our graph"))
            if cnt <= hide_if_over:
                for orphan in orphans_not_in_graph:
                    tree.append((1, orphan))

        if orphans_unlinked:
            cnt = len(orphans_unlinked)
            tree.append((0,
                         f"Concept set also includes {cnt} {'hidden ' if cnt > hide_if_over else ''}nodes unconnected to others in the concept set"))
            if cnt <= hide_if_over:
                for orphan in orphans_unlinked:
                    tree.append((1, orphan))

        for vocab in hidden_dict.keys():
            hidden_concept_ids = hidden_dict[vocab]
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
        await rpt.finish(rows=len(sg))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return {'edges': list(sg.edges), 'layout': layout, 'filled_gaps': missing_in_between_nodes}


def get_concepts_for_graph(codeset_ids: List[int], extra_concept_ids: List[int],
                           hide_vocabs: List[str]):
    _csmi = get_cset_members_items(codeset_ids=codeset_ids)
    # concepts = get_concepts(extra_concept_ids)
    # give hidden rxnorm ext count
    hidden_dict: Dict[str, Set[int]] = {}
    for vocab in hide_vocabs:  # for each vocab being hidden, separate out the concepts
        hidden_nodes = set([c['concept_id'] for c in _csmi if c['vocabulary_id'] == vocab])
        if hidden_nodes:
            hidden_dict[vocab] = hidden_nodes

    hidden_nodes = set().union(*list(hidden_dict.values()))
    csmi = set()
    csmi.update([c for c in _csmi if c not in hidden_nodes])
    return csmi, hidden_dict



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


# def get_connected_subgraph(REL_GRAPH: nx.Graph, nodes: Set[int]) -> (
#     DiGraph, Set[int], Set[int], Set[int], Dict[str, Set[int]]):
#
#     missing_in_between_nodes = get_missing_in_between_nodes(REL_GRAPH, nodes).copy()
#     # sg = connect_nodesOLD(REL_GRAPH, nodes_in_graph, preferred_concept_ids).copy()
#     return nodes_in_graph, missing_in_between_nodes, preferred_concept_ids, orphans_not_in_graph, hidden_nodes, hidden_dict


def get_connected_subgraph(
    REL_GRAPH: nx.Graph,
    codeset_ids: List[int],
    extra_concept_ids: Union[List[int], None] = [],
    hide_vocabs: Union[List[str], None] = []
) -> (DiGraph, Set[int], Set[int], Set[int], Dict[str, Set[int]]):
    pass


print_stack = lambda s: ' | '.join([f"{n} => {','.join([str(x) for x in p])}" for n,p in s])
def get_missing_in_between_nodes(G, subgraph_nodes):
    missing_in_between_nodes = set()
    missing_in_between_nodes_tmp = set()
    sg = G.subgraph(subgraph_nodes)
    leaves = [node for node, degree in sg.out_degree() if degree == 0]
    visited = set()

    for leaf_node in leaves:
        # stack = [(leaf_node, iter(G.predecessors(leaf_node)))]
        descending_from = None
        stack = [(leaf_node, list(reversed(list(G.predecessors(leaf_node)))))]

        while stack:
            # if descending_from:
                # if descending_from in subgraph_nodes:
                #     missing_in_between_

            current_node, predecessors = stack[-1]
            print(f"{str(print_stack(stack)):58} {(descending_from or ''):8} {','.join([str(n) for n in missing_in_between_nodes])} | {','.join([str(n) for n in missing_in_between_nodes_tmp])}")

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
                    stack.append((next_node, list(reversed(list(G.predecessors(next_node))))))
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


# TODO: get test to pass
def tst_graph_code():
    """Tests for graph related functionality

    Siggie would prefer if we declared nodes in groups; would help for readability. Joe doesn't know how that would work."""
    # - Test: Gap filling
    #   Source: depth first of https://app.diagrams.net/#G1mIthDUn4T1y1G3BdupdYKPkZVyQZ5XYR
    # test code for the above:
    # subgraph edges (from definitions and expansions)
    # (2, 1), (2, 8), (4, 3), (4, 10), (10, 9), (10, 12), (11, 10), (11, 13), (15, 14), (15, 18), (20, 16), (20, 19),
    # outside_scope_edges
    # ('root', '2p1'), ('2p1', 2), ('root', '2p2'), ('2p2', 2), ('root', 'cloud'), ('cloud', 8), ('cloud', 6), (6, 5),
    # (6, 11), (6, 17), ('cloud', 15), ('cloud', 20),
    # missing in between edges
    # (8, 7), (7, 5), (5, 4), (18, 17), (17, 16),
    whole_graph_edges = [   # now, more or less, in diagram number order
        (2, 1),
        ('root', '2p1'), ('2p1', 2), ('root', '2p2'), ('2p2', 2), ('root', 'cloud'),
        (4, 3),
        (5, 4),
        (7, 5),
        (8, 7),
        ('cloud', 8),
        (2, 8),
        (6, 5),
        ('cloud', 6),
        (10, 9),
        (4, 10),
        (10, 12),
        (11, 10),
        (6, 11),
        (11, 13),
        (15, 14),
        ('cloud', 15),
        (16, 21),
        (17, 16),
        (6, 17),
        (18, 17),
        (15, 18),
        (20, 16),
        ('cloud', 20),
        (22, 23),
        (19, 22),
        (20, 19),
    ]
    G = nx.DiGraph(whole_graph_edges)

    graph_nodes = set(list(range(1, 23)))
    # graph_nodes.update(['root', '2p1', '2p2', 'cloud'])
    subgraph_nodes =  graph_nodes - {7, 5, 6, 17}

    expected_missing_in_between_nodes = {5, 7, 17}

    missing_in_between_nodes = get_missing_in_between_nodes(G, subgraph_nodes)
    assert missing_in_between_nodes == expected_missing_in_between_nodes
    pass

    # - Test: tree paths:
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


@router.get("/wholegraph")
def subgraph():
    return list(REL_GRAPH.edges)


def condense_super_nodes(sg, threshhold=10):
    super_nodes = [node for node, degree in sg.out_degree() if degree > threshhold]
    # for node in super_nodes:
    # sg.discard(node) -- n

def expand_super_node(G, subgraph_nodes, super_node):
    sg = G.subgraph(subgraph_nodes)


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
    # - Pre 2024/01/26
    # create_rel_graphs(save_to_pickle=True)
    # G = for_testing()
    # sg = G.subgraph(1,9)
    # G, components = disconnected_subgraphs()
    # sg = connected_subgraph_from_nodes(G, [3, 7, 12])
    # j = graph_to_json(sg)
    # pdump(j)
    # - 2024/01/26
    tst_graph_code()
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
