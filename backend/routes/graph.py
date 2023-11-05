import os, warnings
from pathlib import Path

from typing import List, Union #, Dict, Set
from fastapi import APIRouter, Query, Request
# from fastapi.responses import JSONResponse
# from fastapi.responses import Response
# from fastapi.encoders import jsonable_encoder
# from collections import OrderedDict
import networkx as nx
import pickle
from backend.config import CONFIG
from backend.db.utils import sql_query, get_db_connection
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


@router.post("/subgraph")
async def subgraph_post(request: Request, id: Union[List[int], None] = None) -> List:
    rpt = Api_logger()
    await rpt.start_rpt(request, params={'concept_ids': id})

    try:
        sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
        edges = [(str(e[0]), str(e[1])) for e in sg.edges]
        await rpt.finish(rows=len(edges))
    except Exception as e:
        await rpt.log_error(e)
        raise e
    return edges


@router.get("/subgraph")
async def subgraph(request: Request, id: List[int] = Query(...)):   # id is a list of concept ids
    return await subgraph_post(request=request, id=id)


@router.get("/hierarchy")
def hierarchy(id: List[int] = Query(...)):   # id is a list of concept ids
    """
        couldn't figure out how to send the hierarchy in order of nodes with most
        descendants first -- was able to sort it, but fastapi just resorted it in
        key order before sending. going to try to do all the hierarchy stuff at the
        front end instead. including the gap filling.
    """
    sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
    j = graph_to_json(sg)
    return j
    # return [json.dumps(j)]
    # return Response(content=json.dumps(j), media_type='application/json')
    # return JSONResponse(OrderedDict(j))
    # return OrderedDict(j)



def connected_subgraph_from_nodes(nodes, G, G_undirected=None, verbose=False):
    # what this fails to do is fill in gaps if the subgraph is already connected
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

def graph_to_json(G, sorted=False):
    root_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
    if sorted:
        root_nodes = sort_by_most_descendants(G, root_nodes)
    hierarchies = {root: create_hierarchy(G, root, sorted) for root in root_nodes}
    return hierarchies


def create_hierarchy(G, node, sorted=False):
    successors = list(G.successors(node))
    if len(successors) == 0:
        return None
    if sorted:
        successors = sort_by_most_descendants(successors)
    else:
        return {successor: create_hierarchy(G, successor, sorted) for successor in successors}

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
        edges = [tuple(e.values()) for e in rels]
        G = nx.from_edgelist(edges, nx.DiGraph)
        if save_to_pickle:
            timer(f'write pickle for G with {len(G.nodes)} nodes')
            # nx.write_gpickle(G, GRAPH_PATH)   # networkx 4 doesn't have its own pickle
            with open(GRAPH_PATH, 'wb') as f:
                pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
        timer('make undirected version')
        Gu = G.to_undirected()
        if save_to_pickle:
            timer('write pickle for that')
            # nx.write_gpickle(Gu, GRAPH_UNDIRECTED_PATH)
            with open(GRAPH_UNDIRECTED_PATH, 'wb') as f:
                pickle.dump(Gu, f, pickle.HIGHEST_PROTOCOL)
        timer('done')
        return G, Gu


def load_relationship_graphs(save_if_not_exists=True):
    timer = get_timer('./load_relationship_graph')
    G = None
    if os.path.isfile(GRAPH_PATH):
        timer(f'loading {GRAPH_PATH}')
        # G = nx.read_gpickle(GRAPH_PATH)
        with open(GRAPH_PATH, 'rb') as f:
            G = pickle.load(f)
    if G and os.path.isfile(GRAPH_UNDIRECTED_PATH):
        timer(f'loaded {commify(len(G.nodes))}; loading {GRAPH_UNDIRECTED_PATH}')
        # Gu = nx.read_gpickle(GRAPH_UNDIRECTED_PATH)
        with open(GRAPH_UNDIRECTED_PATH, 'rb') as f:
            Gu = pickle.load(f)
        timer(f'loaded {commify(len(Gu.nodes))}')
    else:
        G, Gu = create_rel_graphs(save_if_not_exists)
    timer('done')
    return G, Gu


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
        REL_GRAPH, REL_GRAPH_UNDIRECTED = load_relationship_graphs(save_if_not_exists=True)
    else:
        print(f"Imported from {CONFIG['importer']}, not loading relationship graphs")
