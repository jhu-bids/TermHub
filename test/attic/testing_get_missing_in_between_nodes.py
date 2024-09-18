"""Testing get_missing_in_between_nodes()

TODO: As of 2024/11 this is deprecated. Siggie made a note on get_missing_in_between_nodes() that it is not being used
 anymore.
 If we want to re-use this, should do the following:
 i. correct imports so it will work (this was previously at the root dir)
 ii. Use unittest module to execute these tests

todo: @Siggie: (1) Should this be a proper Python test file?, (2) I moved test_get_missing_in_between_nodes() here
 because the Python debugger was making that file run this as a test instead of doing what I wanted. But IDK if this
 breaks anything for you.
"""
import networkx as nx
import builtins

from networkx import DiGraph

builtins.DONT_LOAD_GRAPH = True
# from backend.routes.graph import get_missing_in_between_nodes, test_get_missing_in_between_nodes
from backend.routes.graph import get_missing_in_between_nodes

print_stack = lambda s: '; '.join([f"""{n}{'<--' if p else ''}{','.join(p)}""" for n,p in reversed(s)])


def testing_get_missing_in_between_nodes(
    whole_graph_edges=None, non_subgraph_nodes=None, expected_missing_in_between_nodes=None, subgraph_nodes=None,
    fail=True, verbose=False
):
    # add code to load whole REL_GRAPH
    # noinspection PyPep8Naming
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


def get_missing(edges, subgraph_nodes, verbose=False):
    G = nx.DiGraph(edges)
    n = get_missing_in_between_nodes(G, subgraph_nodes, verbose=verbose)
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

testing_get_missing_in_between_nodes(test_edges,
                                     subgraph_nodes=subgraph_nodes,
                                     expected_missing_in_between_nodes=expected_missing_in_between_nodes,
                                     fail=False)
# get_missing(test_edges, subgraph_nodes)
