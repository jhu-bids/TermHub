"""TermHub backend

Resources
- https://github.com/tiangolo/fastapi
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.config import CONFIG, override_schema
CONFIG['importer'] = 'app.py'
from backend.routes import cset_crud, db, graph

# users on the same server
# APP = FastAPI()
APP = FastAPI(client_max_size=100_000_000) # trying this, but it shouldn't be necessary
APP.include_router(cset_crud.router)
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
async def set_schema_globally(request: Request, call_next):
    print(request.url)
    # if request.url.path == "/usage": return request

    schema = request.query_params.get("schema")
    if schema:
        override_schema(schema)

    response = await call_next(request)
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


# from fastapi import HTTPException
# import asyncio
# from starlette.responses import JSONResponse
# from starlette.status import HTTP_504_GATEWAY_TIMEOUT
# REQUEST_TIMEOUT_ERROR = 10
# # from https://github.com/tiangolo/fastapi/issues/1752
# # Adding a middleware returning a 504 error if the request processing time is above a certain threshold
# @APP.middleware("http")
# async def timeout_middleware(request: Request, call_next):
#     try:
#         start_time = time.time()
#         return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_ERROR)
#
#     except asyncio.TimeoutError:
#         process_time = time.time() - start_time
#         return JSONResponse({'detail': 'Request processing time excedeed limit',
#                              'processing_time': process_time},
#                             status_code=HTTP_504_GATEWAY_TIMEOUT)


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
