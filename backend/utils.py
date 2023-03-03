"""Backend utilities"""
import functools
import json
import operator
import traceback
from functools import reduce
from typing import Any, Dict, List, Union
from datetime import datetime

from starlette.responses import JSONResponse

JSON_TYPE = Union[Dict, List]


def get_timer(name:str='Timer'):
    steps = []
    def step(msg:str=''):
        done = msg == 'done'
        msg = f'{name} step {len(steps)+1} {msg}'
        t = datetime.now()
        i = None
        if len(steps):
            last_step = steps[-1]
            i = (t - last_step['t']).seconds
        steps.append({'msg': msg, 't': t, 'i': i})
        if len(steps) > 1:
            print(f"{last_step['msg']} completed in {steps[-1]['i']} seconds")
        if done:
            print(f"{name} completed in {(t - steps[0]['t']).seconds} seconds")
    return step

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


def return_err_with_trace(func):
    """Handle exceptions"""
    @functools.wraps(func)
    def decorated_func(*args, **kwargs):
        """Handle exceptions"""
        try:
            return func(*args, **kwargs)
        except Exception as err:
            stacktrace = "".join(traceback.format_exception(etype=type(err), value=err, tb=err.__traceback__))
            return JSONResponse(
              status_code=500,
              content={
                  "status": "error",
                  "error": str(err),
                  "stacktrace": stacktrace.split('\n')})
    return decorated_func


# No longer using this inject stuff. got rid of circular imports
# But this was how it was used:
#
#     inject_to_avoid_circular_imports('get_concepts', get_concepts)
#     inject_to_avoid_circular_imports('CON', CON)
#
# INJECTED_STUFF = {}
# def inject_to_avoid_circular_imports(name, obj):
#     INJECTED_STUFF[name] = obj