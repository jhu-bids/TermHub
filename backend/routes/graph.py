import os, warnings
import csv
import io
from pathlib import Path

from typing import List, Union, Tuple #, Dict, Set

import networkx
from fastapi import APIRouter, Query, Request
# from fastapi.responses import JSONResponse
# from fastapi.responses import Response
# from fastapi.encoders import jsonable_encoder
# from collections import OrderedDict
import networkx as nx
import pickle
from sqlalchemy.sql import text

from backend.config import CONFIG
from backend.db.utils import sql_query, get_db_connection, SCHEMA
from backend.api_logger import Api_logger
from backend.utils import pdump, get_timer, commify

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


@router.get("/indented-concept-list")
async def indented_concept_list(request: Request, id: List[int] = Query(...)):   # id is a list of concept ids
    return await indented_concept_list_post(request=request, id=id)


@router.post("/indented-concept-list")
async def indented_concept_list_post(request: Request, id: Union[List[int], None] = None) -> List:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'concept_ids': id})

    try:
        # new way to do this
        paths = all_paths(REL_GRAPH, id)
        tree = paths_as_indented_tree(paths)
        await rpt.finish(rows=len(tree))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return tree


def all_paths(g: networkx.DiGraph, nodes: List[int]) -> List[List[int]]:
    """
    Creates a subgraph from g using nodes.
    Identifies root and leaf nodes in this subgraph.
    Generates all simple paths from each root to each leaf in the original graph g.
    Returns the list of all such paths.
    """
    sg = g.subgraph(nodes)
    roots = [node for node, degree in sg.in_degree() if degree == 0]
    leaves = [node for node, degree in sg.out_degree() if degree == 0]
    paths = []
    for root in roots:
        for leaf in leaves:
            _paths = list(nx.all_simple_paths(g, root, leaf))
            for path in _paths:
                if len(path) > 1:
                    paths.append(path)
    return paths


def fill_in_gaps(G, nodes):
    sg = G.subgraph(nodes)
    roots = [node for node, degree in sg.in_degree() if degree == 0]
    leaves = [node for node, degree in sg.out_degree() if degree == 0]
    missing_nodes = []  # nodes needed to traverse all paths but not present in nodes list
    for root in roots:
        for leaf in leaves:
            _paths = list(nx.all_simple_paths(G, root, leaf))
            for path in _paths:
                for node in path:
                    if node not in nodes:
                        missing_nodes.append(node)
    sgc = G.subgraph(nodes + missing_nodes)
    return sgc


def paths_as_indented_tree(paths: List[List[int]]) -> List[Tuple[int, int]]:
    """
    paths: A list of paths (each path is a list of node identifiers).
    Initializes a root TreeNode with None value.
    Inserts each path into this tree.
    Generates a list of lines where each line represents a level and a node identifier in the indented tree.
    """
    # Initialize tree and insert paths
    root = TreeNode(None)  # Root node doesn't hold any data
    # paths = [("A", "B", "C"), ("A", "B", "D"), ("E", "B", "C"), ("E", "B", "D")]
    for path in paths:
        root.insert(path)

    tree = []
    for line in generate_csv_lines(root):
        # tree.append({'level': line[0], 'concept_id': line[1]})
        tree.append((line[0], line[1]))

    return tree


class TreeNode:
    """TODO: document how this works, what it's for (got it from chatgpt)"""
    """
    Purpose: Represents a node in the tree, used to construct the indented tree structure.
    Attributes:
    value: The value (or identifier) of the node.
    children: A dictionary of child nodes.
    Methods:
    __init__(self, value): Constructor to initialize the node with a value.
    insert(self, path): Inserts a path into the tree, starting from this node.
    """
    def __init__(self, value):
        self.value = value
        self.children = {}

    def insert(self, path):
        if path:
            head, *tail = path
            if head not in self.children:
                self.children[head] = TreeNode(head)
            self.children[head].insert(tail)


def condense_super_nodes(sg, threshhold=10):
    super_nodes = [node for node, degree in sg.out_degree() if degree > threshhold]
    # for node in super_nodes:
    # sg.remove_node(node) -- n

def expand_super_node(G, subgraph_nodes, super_node):
    sg = G.subgraph(subgraph_nodes)


def generate_csv_lines(node, level=-1):
    if node.value is not None:  # Skip the root node
        yield level, node.value
    for child in node.children.values():
        yield from generate_csv_lines(child, level + 1)


# @router.post("/subgraph")
# async def subgraph_post(request: Request, id: Union[List[int], None] = None) -> List:
#     rpt = Api_logger()
#     await rpt.start_rpt(request, params={'concept_ids': id})
#
#     try:
#         sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
#         edges = [(str(e[0]), str(e[1])) for e in sg.edges]
#         await rpt.finish(rows=len(edges))
#     except Exception as e:
#         await rpt.log_error(e)
#         raise e
#     return edges
#
#
# @router.get("/subgraph")
# async def subgraph(request: Request, id: List[int] = Query(...)):   # id is a list of concept ids
#     return await subgraph_post(request=request, id=id)
#
#
# @router.get("/hierarchy")
# def hierarchy(id: List[int] = Query(...)):   # id is a list of concept ids
#     """
#         couldn't figure out how to send the hierarchy in order of nodes with most
#         descendants first -- was able to sort it, but fastapi just resorted it in
#         key order before sending. going to try to do all the hierarchy stuff at the
#         front end instead. including the gap filling.
#     """
#     sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
#     j = graph_to_json(sg)
#     return j
#     # return [json.dumps(j)]
#     # return Response(content=json.dumps(j), media_type='application/json')
#     # return JSONResponse(OrderedDict(j))
#     # return OrderedDict(j)

# def generate_csv(paths):
#     # Initialize tree and insert paths
#     root = TreeNode(None)  # Root node doesn't hold any data
#     # paths = [("A", "B", "C"), ("A", "B", "D"), ("E", "B", "C"), ("E", "B", "D")]
#     for path in paths:
#         root.insert(path)
#
#     # Use StringIO to create a CSV string
#     output = io.StringIO()
#     writer = csv.writer(output)
#     writer.writerow(['level', 'node'])  # Writing header
#     for line in generate_csv_lines(root):
#         writer.writerow(line)
#
#     # Get the CSV string from StringIO
#     csv_string = output.getvalue()
#     output.close()
#
#     # csv_string contains the CSV data
#     return csv_string


# def connected_subgraph_from_nodes(nodes, G, G_undirected=None, verbose=False):
#     # what this fails to do is fill in gaps if the subgraph is already connected
#     timer = get_timer('  connected_subgraph_from_nodes')
#     if not G_undirected:
#         verbose and timer(f'convert G to undirected')
#         G_undirected = G.to_undirected()
#
#     verbose and timer(f'subgraph for {len(nodes)} nodes')
#     sg = G.subgraph(nodes)
#     verbose and timer('get roots')
#     roots = get_roots(sg)
#     pairs = [(roots[i], roots[i+1]) for i in range(0, len(roots) - 1)]
#     connected_nodes = set(nodes)
#     verbose and timer(f'get shortest paths for {len(pairs)} pairs of root nodes')
#     for p in pairs:
#         try:
#             verbose and timer(f'   path between {p[0]} and {p[1]}')
#             path = nx.shortest_path(G_undirected, *p)
#             connected_nodes.update(path)
#         except Exception as err:
#             warnings.warn(str(err))
#     verbose and timer(f'subgraph for {len(connected_nodes)} connected nodes')
#     sgc = G.subgraph(connected_nodes)
#     verbose and timer('done')
#     return sgc
#
#
# def sort_by_most_descendants(G, nodes):
#     key = lambda n: len(nx.descendants(G, n))
#     return sorted(nodes, key=key, reverse=True)
#
# def graph_to_json(G, sorted=False):
#     root_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
#     if sorted:
#         root_nodes = sort_by_most_descendants(G, root_nodes)
#     hierarchies = {root: create_hierarchy(G, root, sorted) for root in root_nodes}
#     return hierarchies
#
#
# def create_hierarchy(G, node, sorted=False):
#     successors = list(G.successors(node))
#     if len(successors) == 0:
#         return None
#     if sorted:
#         successors = sort_by_most_descendants(successors)
#     else:
#         return {successor: create_hierarchy(G, successor, sorted) for successor in successors}
#
# def for_testing():
#     G = nx.DiGraph()
#     G.add_edges_from([(1, 2), (1, 3), (2, 4), (2, 5), (2,3), (2, 6), (3, 6), (9,2)])
#     return G
#
#
# def disconnected_subgraphs():
#     G = nx.DiGraph([
#         (1, 2), (2, 3), (3, 4),
#         (1, 5), (5, 6), (6, 7),
#         (10, 11), (11, 12), (12, 6)
#     ])
#     components = G.subgraph([2,3,4,5,6,7])
#     return G, components



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

    timer('make graph')
    G = nx.DiGraph()
    for source, target in edge_generator:
        G.add_edge(source, target)

    # edges = [tuple(e.values()) for e in rels]
    # G = nx.from_edgelist(edges, nx.DiGraph)
    if save_to_pickle:
        timer(f'write pickle for G with {len(G.nodes)} nodes')
        # nx.write_gpickle(G, GRAPH_PATH)   # networkx 4 doesn't have its own pickle
        with open(GRAPH_PATH, 'wb') as f:
            pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
    # timer('make undirected version')
    # Gu = G.to_undirected()
    # if save_to_pickle:
    #     timer('write pickle for that')
    #     # nx.write_gpickle(Gu, GRAPH_UNDIRECTED_PATH)
    #     with open(GRAPH_UNDIRECTED_PATH, 'wb') as f:
    #         pickle.dump(Gu, f, pickle.HIGHEST_PROTOCOL)
    timer('done')
    return G # , Gu


def load_relationship_graph(save_if_not_exists=True):
    timer = get_timer('./load_relationship_graph')
    G = None
    timer(f'loading {GRAPH_PATH}')
    if os.path.isfile(GRAPH_PATH):
        # G = nx.read_gpickle(GRAPH_PATH)
        with open(GRAPH_PATH, 'rb') as f:
            G = pickle.load(f)
    # if G and os.path.isfile(GRAPH_UNDIRECTED_PATH):
    #     timer(f'loaded {commify(len(G.nodes))}; loading {GRAPH_UNDIRECTED_PATH}')
    #     # Gu = nx.read_gpickle(GRAPH_UNDIRECTED_PATH)
    #     with open(GRAPH_UNDIRECTED_PATH, 'rb') as f:
    #         Gu = pickle.load(f)
    #     timer(f'loaded {commify(len(Gu.nodes))}')
    else:
        # G, Gu = create_rel_graphs(save_if_not_exists)
        G = create_rel_graphs(save_if_not_exists)
    timer('done')
    return G # , Gu


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
    if CONFIG['importer'] == 'app.py':
        # REL_GRAPH, REL_GRAPH_UNDIRECTED = load_relationship_graph(save_if_not_exists=True)
        REL_GRAPH = load_relationship_graph(save_if_not_exists=True)
    else:
        print(f"Imported from {CONFIG['importer']}, not loading relationship graphs")
