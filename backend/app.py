"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import os
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
# from starlette.requests import Request
import time
import datetime
from socket import gethostname

from backend.routes import cset_crud, db, graph
from backend.db.config import override_schema, get_schema_name
from backend.db.utils import insert_from_dict, get_db_connection

PROJECT_DIR = Path(os.path.dirname(__file__)).parent
# users on the same server
APP = FastAPI()
APP.include_router(cset_crud.router)
# APP.include_router(oak.router)
APP.include_router(graph.router)
APP.include_router(db.router)
APP.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)
APP.add_middleware(GZipMiddleware, minimum_size=1000)

@APP.middleware("http")
async def set_schema_globally_and_log_calls(request: Request, call_next):
    """
    This is middleware and will be EXECUTED ON EVERY API CALL
    Its purpose is to log TermHub usage to help us prioritize performance improvements

    Also, if a schema is provided, it will be used to override CONFIG['schema']
    """

    url = request.url
    query_params = request.query_params # Extracting query params as a dict

    codeset_ids = query_params.getlist("codeset_ids")
    if not codeset_ids:
        print(f"No codeset_ids provided, not sure what monitoring to do, if any for {url}")
        return await call_next(request)
    if len(codeset_ids) == 1 and type(codeset_ids[0]) == str:
        codeset_ids = codeset_ids[0].split('|')
    codeset_ids = [int(x) for x in codeset_ids]

    start_time = time.time()

    rpt = {}

    rpt['host'] = os.getenv('HOSTENV', gethostname())

    # rpt['client'] = request.client.host -- this gives a local (169.154) IP on azure
    #   chatgpt recommends:
    forwarded_for: Optional[str] = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # The header can contain multiple IP addresses, so take the first one
        rpt['client'] = forwarded_for.split(',')[0]
    else:
        rpt['client'] = request.client.host

    schema = query_params.get("schema")
    if schema:
        override_schema(schema)

    schema = get_schema_name()
    rpt['schema'] = schema

    api_call = url.components[2][1:] # string leading /
    rpt['api_call'] = api_call


    if api_call == 'concept-ids-by-codeset-id':
        rpt['related_codeset_ids'] = len(codeset_ids)
    else:
        rpt['codeset_ids'] = codeset_ids

    print(f"Request: {request.url} {request.method} {schema} {codeset_ids}")

    response = await call_next(request) # Proceed with the request

    end_time = time.time()
    process_seconds = end_time - start_time

    rpt['timestamp'] = datetime.datetime.now().isoformat()
    rpt['process_seconds'] = process_seconds

    with get_db_connection() as con:
        insert_from_dict(con, 'public.api_runs', rpt, skip_if_already_exists=False)

    response.headers["X-Process-Time"] = str(process_seconds)
    return response


def run(port: int = 8000):
    """Run app"""
    uvicorn.run(APP, host='0.0.0.0', port=port)


@APP.get("/")
def read_root():
    """Root route"""
    # noinspection PyUnresolvedReferences
    url_list = [{"path": route.path, "name": route.name} for route in APP.routes]
    return url_list

# CACHE_FILE = "cache.pickle"
#
#
# def load_cache(maxsize):
#     try:
#         with open(CACHE_FILE, "rb") as f:
#             return pickle.load(f)
#     except (FileNotFoundError, pickle.UnpicklingError):
#         return LRU(maxsize)
#
# def save_cache(cache):
#     with open(CACHE_FILE, "wb") as f:
#         pickle.dump(cache, f)
#
#
# @APP.on_event("shutdown")
# async def save_cache_on_shutdown():
#     save_cache(cache)
#
#
# def memoize(maxsize=1000):
#     # TODO: allow passing in CACHE_FILE and maxsize
#     cache = load_cache(maxsize)
#
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#
#             # to prevent TypeError: unhashable type: 'list' :
#             t = tuple('|'.join([str(x) for x in a]) if type(a) == list else a for a in args)
#
#             key = (t, tuple(sorted(kwargs.items())))
#
#             if key in cache:
#                 return cache[key]
#             result = func(*args, **kwargs)
#             cache[key] = result
#             return result
#         return wrapper
#     return decorator
#
# cache = memoize(maxsize=1000)


if __name__ == '__main__':
    run()


def monitor_request(request: Request, codeset_ids: List[int]) -> None:

    pass
