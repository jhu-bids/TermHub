import warnings
from typing import List # , Union, Dict, Set
from fastapi import APIRouter, Query
import networkx as nx
from backend.db.utils import sql_query, get_db_connection
from backend.utils import pdump, get_timer, commify

VERBOSE = True

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

@router.get("/subgraph/")
def subgraph(id: List[int] = Query(...)):   # id is a list of concept ids
    sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
    return list(sg.edges)


@router.get("/hierarchy/")
def hierarchy(id: List[int] = Query(...)):   # id is a list of concept ids
    sg = connected_subgraph_from_nodes(id, REL_GRAPH, REL_GRAPH_UNDIRECTED)
    j = graph_to_json(sg)
    return j



def connected_subgraph_from_nodes(nodes, G, G_undirected=None):
    timer = get_timer('  connected_subgraph_from_nodes')
    if not G_undirected:
        VERBOSE and timer(f'convert G to undirected')
        G_undirected = G.to_undirected()

    VERBOSE and timer(f'subgraph for {len(nodes)} nodes')
    sg = G.subgraph(nodes)
    VERBOSE and timer('get roots')
    roots = get_roots(sg)
    pairs = [(roots[i], roots[i+1]) for i in range(0, len(roots) - 1)]
    connected_nodes = set(nodes)
    VERBOSE and timer(f'get shortest paths for {len(pairs)} pairs of root nodes')
    for p in pairs:
        try:
            timer(f'   path between {p[0]} and {p[1]}')
            path = nx.shortest_path(G_undirected, *p)
            connected_nodes.update(path)
        except Exception as err:
            warnings.warn(str(err))
    VERBOSE and timer(f'subgraph for {len(connected_nodes)} connected nodes')
    sgc = G.subgraph(connected_nodes)
    VERBOSE and timer('done')
    return sgc


def graph_to_json(G):
    root_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
    hierarchies = {root: create_hierarchy(G, root) for root in root_nodes}
    return hierarchies


def create_hierarchy(graph, node):
    successors = list(graph.successors(node))
    if len(successors) == 0:
        return None
    else:
        return {successor: create_hierarchy(graph, successor) for successor in successors}

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


def load_relationship_graph():
    return nx.read_gpickle('./networkx/relationship_graph.pickle')


def load_relationship_graph_undirected():
    return nx.read_gpickle('./networkx/relationship_graph_undirected.pickle')

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
    if LOAD_RELGRAPH:
        if LOAD_FROM_PICKLE:
            timer = get_timer('./load_relationship_graph')
            timer('loading REL_GRAPH')
            REL_GRAPH = load_relationship_graph()
            timer(f'loaded {commify(len(REL_GRAPH.nodes))}; loading REL_GRAPH_UNDIRECTED')
            REL_GRAPH_UNDIRECTED = load_relationship_graph_undirected()
            timer(f'loaded {commify(len(REL_GRAPH_UNDIRECTED.nodes))}')
            timer('done')
        else:
            REL_GRAPH, REL_GRAPH_UNDIRECTED = create_rel_graphs(save_to_pickle=False)



        # sg = G.subgraph([7,3])
            # roots = get_roots(sg)
