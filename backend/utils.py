"""Backend utilities"""
import json
import operator
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, Tuple, Union


def cnt(vals):
    """Count values"""
    return len(set(vals))


def commify(n):
    """Those dirty commies"""
    return f'{n:,}'


def dump(o):
    """Return pretty printed json"""
    return json.dumps(o, indent=2)


def pdump(o):
    """Prent pretty printed json"""
    print(dump(o))


class Bunch(object):
    """dictionary to namespace, a la https://stackoverflow.com/a/2597440/1368860"""
    def __init__(self, adict):
        """Init"""
        self.__dict__.update(adict)

    def to_dict(self):
        """Convert to dictionary"""
        return self.__dict__


def get_nested_from_dict(d: Dict, key_path: List):
    """Get nested value from dictionary"""
    return reduce(operator.getitem, key_path, d)


def set_nested_in_dict(d: Dict, key_path: List, value: Any):
    """Set nested value in dictionary"""
    # noinspection PyUnresolvedReferences
    get_nested_from_dict(d, key_path[:-1])[key_path[-1]] = value


# todo: typically takes 2 seconds on several 100 selected_parent_ids. any way to speed up?
def hierarchify_list_of_parent_kids(
    parent_child_list: List[Tuple[Union[str, int], Union[str, int]]],
    selected_parent_ids: List[Union[str, int]] = None
) -> Dict:
    """Convert a list of tuples of (parent, child) to a hierarchy

    Example:
        parent_sib_list: [(3290077, 3219427), (3219427, 3429308), (3219427, 3458111), (3457827, 3465375)]
        returns: {
          3290077: {
            3219427: {
              3429308: {},
              3458111: {}
          },
          3457827: {
            3465375: {},
          }
    """
    if not selected_parent_ids:
        selected_parent_ids = [x[0] for x in parent_child_list]

    # Initialize reusable map of parents and all their children
    t1 = datetime.now()
    parent_children_map = {concept_id: set() for pair in parent_child_list for concept_id in pair}
    for parent, child in parent_child_list:
        parent_children_map[parent].add(child)

    # Build hierarchy
    d = {}
    added = set()

    def traverse(path: List[Union[str, int]]):
        """Recursive function. Given 2 variables in outer scope, parent_children_map (dict of parents with values as
        list of their children), added (set of nodes already fully traversed), and d, and given a parameter
        path, which is a list of concept_ids, traverse the hierarchy, keep track of fully traversed nodes, and create a
        subsumption hierarchy out of d."""
        current_node = path[-1]
        kids = parent_children_map.get(current_node, {})
        if current_node not in added:
            set_nested_in_dict(d, path, {k: {} for k in kids})
        for kid in kids:
            traverse(path + [kid])
        added.add(current_node)

    for _id in selected_parent_ids:
        traverse([_id])

    # Return
    t2 = datetime.now()
    print(f"Time to traverse: {t2 - t1}")
    return d
