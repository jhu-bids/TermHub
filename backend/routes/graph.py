import os, warnings
import json
# from functools import cache
from pathlib import Path

from typing import List # , Union, Dict, Set
from fastapi import APIRouter, Query
# from fastapi.responses import JSONResponse
# from fastapi.responses import Response
# from fastapi.encoders import jsonable_encoder
# from collections import OrderedDict
import networkx as nx
from backend.db.utils import sql_query, get_db_connection
from backend.utils import pdump, get_timer, commify

VERBOSE = True
PROJECT_DIR = Path(os.path.dirname(__file__)).parent.parent
VOCABS_PATH = os.path.join(PROJECT_DIR, 'termhub-vocab')

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

@router.get("/wholegraph/")
def subgraph():
    return list(REL_GRAPH.edges)


@router.get("/subgraph/")
def subgraph(id: List[int] = Query(...)):   # id is a list of concept ids
    sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
    return list(sg.edges)


@router.get("/hierarchy/")
def hierarchy(id: List[int] = Query(...)):   # id is a list of concept ids
    """
        couldn't figure out how to send the hierarchy in order of nodes with most
        descendants first -- was able to sort it, but fastapi just resorted it in
        key order before sending. going to try to do all the hierarchy stuff at the
        front end instead. including the gap filling.
    """
    sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
    j = graph_to_json(sg)
    return [json.dumps(j)]
    # return Response(content=json.dumps(j), media_type='application/json')
    # return JSONResponse(OrderedDict(j))
    # return OrderedDict(j)



def connected_subgraph_from_nodes(nodes, G, G_undirected=None, verbose=False):
    timer = get_timer('  connected_subgraph_from_nodes')
    if not G_undirected:
        verbose and timer(f'convert G to undirected')
        G_undirected = G.to_undirected()

    verbose and timer(f'subgraph for {len(nodes)} nodes')
    sg = G.subgraph(nodes)
    verbose and timer('get roots')
    roots = get_roots(sg)
    pairs = [(roots[i], roots[i+1]) for i in range(0, len(roots) - 1)]
    connected_nodes = set(nodes)
    verbose and timer(f'get shortest paths for {len(pairs)} pairs of root nodes')
    for p in pairs:
        try:
            verbose and timer(f'   path between {p[0]} and {p[1]}')
            path = nx.shortest_path(G_undirected, *p)
            connected_nodes.update(path)
        except Exception as err:
            warnings.warn(str(err))
    verbose and timer(f'subgraph for {len(connected_nodes)} connected nodes')
    sgc = G.subgraph(connected_nodes)
    verbose and timer('done')
    return sgc


def sort_by_most_descendants(G, nodes):
    key = lambda n: len(nx.descendants(G, n))
    return sorted(nodes, key=key, reverse=True)

def graph_to_json(G):
    root_nodes = sort_by_most_descendants(G, [node for node in G.nodes if G.in_degree(node) == 0])
    hierarchies = {root: create_hierarchy(G, root) for root in root_nodes}
    return hierarchies


def create_hierarchy(G, node):
    successors = sort_by_most_descendants(G, list(G.successors(node)))
    if len(successors) == 0:
        return None
    else:
        return {successor: create_hierarchy(G, successor) for successor in successors}

def for_testing():
    G = nx.DiGraph()
    G.add_edges_from([(1, 2), (1, 3), (2, 4), (2, 5), (2,3), (2, 6), (3, 6), (9,2)])
    return G


def disconnected_subgraphs():
    G = nx.DiGraph([
        (1, 2), (2, 3), (3, 4),
        (1, 5), (5, 6), (6, 7),
        (10, 11), (11, 12), (12, 6)
    ])
    components = G.subgraph([2,3,4,5,6,7])
    return G, components


def get_roots(G):
    """Return roots of disconnected components of G. (Should be unique list, so not enforcing uniqueness.)"""
    return [n for n in G.nodes if G.in_degree(n) == 0]


def create_rel_graphs(save_to_pickle: bool):
    timer = get_timer('create_rel_graphs')
    with get_db_connection() as con:
        # load_csv(con, 'relationship', 'dataset', schema='n3c')
        # rels = sql_query(con, f"""
        #     SELECT concept_id_1, concept_id_2 -- , relationship_id
        #     FROM n3c.concept_relationship cr
        #     JOIN relationship r ON cr.relationship_id = r.relationship_id
        #     WHERE r.defines_ancestry=1 and r.is_hierarchical=1
        # """)
        timer('get concept_ancestor records')
        rels = sql_query(con, f"""
            SELECT ancestor_concept_id, descendant_concept_id
            FROM n3c.concept_ancestor
            WHERE min_levels_of_separation = 1
        """)
        timer('make graph')
        G = nx.from_edgelist(rels, nx.DiGraph)
        if save_to_pickle:
            timer(f'write pickle for G with {len(G.nodes)} nodes')
            nx.write_gpickle(G, 'networkx/relationship_graph.pickle')
        timer('make undirected version')
        Gu = G.to_undirected()
        if save_to_pickle:
            timer('write pickle for that')
            nx.write_gpickle(Gu, 'networkx/relationship_graph_undirected.pickle')
        timer('done')
        return G, Gu


def load_relationship_graphs(save_if_not_exists=True):
    timer = get_timer('./load_relationship_graph')
    p = os.path.join(VOCABS_PATH, 'relationship_graph.pickle')
    if os.path.isfile(p):
        timer(f'loading {p}')
        G = nx.read_gpickle(p)
    p = os.path.join(VOCABS_PATH, 'relationship_graph_undirected.pickle')
    if G and os.path.isfile(p):
        timer(f'loaded {commify(len(G.nodes))}; loading {p}')
        Gu = nx.read_gpickle(p)
        timer(f'loaded {commify(len(Gu.nodes))}')
    else:
        G, Gu = create_rel_graphs(save_if_not_exists)
    timer('done')
    return G, Gu


LOAD_FROM_PICKLE = False
LOAD_RELGRAPH = True

if __name__ == '__main__':
    pass
    # create_rel_graph(save_to_pickle=True)
    # G = for_testing()
    # sg = G.subgraph(1,9)
    # G, components = disconnected_subgraphs()
    # sg = connected_subgraph_from_nodes(G, [3, 7, 12])
    # j = graph_to_json(sg)
    # pdump(j)
else:
    REL_GRAPH, REL_GRAPH_UNDIRECTED = load_relationship_graphs(save_if_not_exists=True)
