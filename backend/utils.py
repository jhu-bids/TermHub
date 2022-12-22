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


# todo: should this function be merged with hierarchy() in app.py?
def hierarchify_list_of_parent_kids(
    all_parent_child_list: List[Tuple[Union[str, int], Union[str, int]]],
    selected_root_ids: List[Union[str, int]]
) -> Dict:
    """Convert a list of tuples of (parent, child) to a hierarchy, only for selected_root_ids and their descendants.

    Example:
        parent_child_list: [(3290077, 3219427), (3219427, 3429308), (3219427, 3458111), (3457827, 3465375)]
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
    # Initialize reusable map of parents and all their children
    parent_children_map = {concept_id: set() for pair in all_parent_child_list for concept_id in pair}
    for parent, child in all_parent_child_list:
        parent_children_map[parent].add(child)

    # Build hierarchy
    # TODO: Attempt 1: this is here for reference. delete if attempt 2 is works. it's already 200x faster
    # d = {}
    # https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    # def traverse(path: List[Union[str, int]]):
    #     """Recursive function. Given 2 variables in outer scope, parent_children_map (dict of parents with values as
    #     list of their children), added (set of nodes already fully traversed), and d, and given a parameter
    #     path, which is a list of concept_ids, traverse the hierarchy, keep track of fully traversed nodes, and create a
    #     subsumption hierarchy out of d."""
    #     current_node = path[-1]
    #     kids = parent_children_map.get(current_node, {})
    #     set_nested_in_dict(d, path, {k: {} for k in kids})
    #     for kid in kids:
    #         traverse(path + [kid])
    #
    # for _id in selected_parent_ids:
    #     traverse([_id])

    # TODO: Attempt 2: when @Siggie finishes with top_level_cids(), results of that query are passed into here as
    #  selected_root_ids. After that, there will hopefully be no issues left with this hierarchy. But should check and
    #  remove this comment (as well as all of Attempt 1 commented out above) if all is good.
    def recurse(ids):
        x = {}
        for id in ids:
            children = parent_children_map.get(id, [])
            x[id] = recurse(children)
        return x
    d = recurse(selected_root_ids)

    return d
