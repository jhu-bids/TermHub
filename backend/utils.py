"""Backend utilities"""
import json
import operator
from functools import reduce
from typing import Any, Dict, List, Union


JSON_TYPE = Union[Dict, List]


def cnt(vals):
    """Count values"""
    return len(set(vals))


def commify(n):
    """Those dirty commies
    ░░░░░░░░░░▀▀▀██████▄▄▄░░░░░░░░░░
    ░░░░░░░░░░░░░░░░░▀▀▀████▄░░░░░░░
    ░░░░░░░░░░▄███████▀░░░▀███▄░░░░░
    ░░░░░░░░▄███████▀░░░░░░░▀███▄░░░
    ░░░░░░▄████████░░░░░░░░░░░███▄░░
    ░░░░░██████████▄░░░░░░░░░░░███▌░
    ░░░░░▀█████▀░▀███▄░░░░░░░░░▐███░
    ░░░░░░░▀█▀░░░░░▀███▄░░░░░░░▐███░
    ░░░░░░░░░░░░░░░░░▀███▄░░░░░███▌░
    ░░░░▄██▄░░░░░░░░░░░▀███▄░░▐███░░
    ░░▄██████▄░░░░░░░░░░░▀███▄███░░░
    ░█████▀▀████▄▄░░░░░░░░▄█████░░░░
    ░████▀░░░▀▀█████▄▄▄▄█████████▄░░
    ░░▀▀░░░░░░░░░▀▀██████▀▀░░░▀▀██░░
    """
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


INJECTED_STUFF = {}
def inject_to_avoid_circular_imports(name, obj):
    INJECTED_STUFF[name] = obj