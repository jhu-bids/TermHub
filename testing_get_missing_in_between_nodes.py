import networkx as nx
import builtins
builtins.DONT_LOAD_GRAPH = True
from backend.routes.graph import get_missing_in_between_nodes, test_get_missing_in_between_nodes

print_stack = lambda s: '; '.join([f"""{n}{'<--' if p else ''}{','.join(p)}""" for n,p in reversed(s)])

def get_missing(edges, subgraph_nodes):
    G = nx.DiGraph(edges)
    n = get_missing_in_between_nodes(G, subgraph_nodes, verbose=True)
    print(f"Found {n} missing nodes\n")
    return n

graph_as_ascii = """
            a
           / \
          b   i
         /    |
         |    j
         c___/
         |
         d___
        / \  \
       e   h  g
       |   |
        \ /
         f
"""
test_edges = [
    ('a', 'b'),
    ('c', 'd'),
    ('a', 'i'),
    ('i', 'j'),
    ('b', 'c'),
    ('j', 'c'),
    ('d', 'e'),
    ('d', 'g'),
    ('d', 'h'),
    ('e', 'f'),
    ('h', 'f'),
    # ('j', 'k'),     # extra nodes beyond the real-life example, for some other testing
    # ('l', 'h'),
    # ('k', 'h'),
]
# subgraph_nodes = ['f', 'd', ]
# expected_missing_in_between_nodes = ['e', 'h']
subgraph_nodes = ['f', 'd', 'i',]
expected_missing_in_between_nodes = ['e', 'h', 'c', 'j']
# subgraph_nodes = ['f', 'd', 'g', 'k']

test_get_missing_in_between_nodes(test_edges,
                                  subgraph_nodes=subgraph_nodes,
                                  expected_missing_in_between_nodes=expected_missing_in_between_nodes,
                                  fail=False)
# get_missing(test_edges, subgraph_nodes)
