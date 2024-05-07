import networkx as nx
from typing import List, Set, Union
VERBOSE = False

# print_stack = lambda s: ' | '.join([f"""{n} => {str(p).replace("'", "")}""" for n,p in reversed(s)])
print_stack = lambda s: ' | '.join([f"""{n}{'=>' if p else ''}{','.join(p)}""" for n,p in reversed(s)])

# editing this one. keep it and replace graph.py one with it
def get_missing_in_between_nodes(G: nx.DiGraph, subgraph_nodes: Union[List[int], Set[int]], verbose=VERBOSE) -> Set:
    missing_in_between_nodes = set()
    missing_in_between_nodes_tmp = set()
    sg: nx.DiGraph = G.subgraph(subgraph_nodes)
    subgraph_nodes = set(subgraph_nodes)
    # noinspection PyCallingNonCallable
    leaves = [node for node, degree in sg.out_degree() if degree == 0]
    print(leaves)
    # leaves = sorted([node for node, degree in sg.out_degree() if degree == 0])
    visited = set()

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
                    f"--{','.join([str(n) for n in visited]) if visited else ''}"  # <missing nodes>
                )  # {temp missing nodes}

            next_node = predecessors.pop(0) if predecessors else None
            if next_node:
                descending_from = None
                # ignoring visited is messing stuff up visited node is in the graph, i think
                if next_node not in visited:
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
                    visited.add(n)

    return missing_in_between_nodes

def get_missing(edges, subgraph_nodes):
    G = nx.DiGraph(edges)
    n = get_missing_in_between_nodes(G, subgraph_nodes, verbose=True)
    print(f"Found {n} missing nodes\n")
    return n
subgraph_nodes = ['f', 'd', 'g', ]
# subgraph_nodes = ['f', 'd', 'g', 'i',]
# subgraph_nodes = ['f', 'd', 'g', 'k']
















test_edges = [
    ('c', 'd'),
    ('a', 'b'),
    ('i', 'j'),
    ('a', 'i'),
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
get_missing(test_edges, subgraph_nodes)
