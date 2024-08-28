"""Backend utilities"""
import datetime
import time
from itertools import chain, combinations
from functools import wraps, reduce
import threading
import json
import operator
import os
import smtplib
import traceback
from typing import Dict, List, Any
from datetime import datetime
import warnings

from requests import Response, post
from starlette.responses import JSONResponse
# for cancel on disconnect, from https://github.com/RedRoserade/fastapi-disconnect-example/blob/main/app.py

from backend.config import CONFIG


def debounce(wait):
    """ Decorator that will postpone a function's
        execution until after `wait` seconds
        have elapsed since the last time it was invoked.
        from https://chat.openai.com/share/7ed01b5b-97bd-436a-b23b-542f068a4302"""
    def decorator(func):
        def debounced(*args, **kwargs):
            def call_it():
                func(*args, **kwargs)
            if hasattr(debounced, '_timer'):
                debounced._timer.cancel()
            debounced._timer = threading.Timer(wait, call_it)
            debounced._timer.start()
        return wraps(func)(debounced)
    return decorator

# Example usage
@debounce(2)  # Wait for 2 seconds before executing the function
def debounce_test(arg):
    print(f"debounce test called: {arg}")


def throttle(wait = 1):
    """ Decorator that prevents a function from being called
        more than once every `wait` seconds. """
    def decorator(func):
        last_called = [0]  # Use a list to allow nonlocal modification

        @wraps(func)
        def throttled(*args, **kwargs):
            nonlocal last_called
            elapsed = time.time() - last_called[0]
            if elapsed > wait:
                last_called[0] = time.time()
                return func(*args, **kwargs)

        return throttled
    return decorator


# Example usage
@throttle(2)  # Function can only be called once every 2 seconds
def throttle_test(arg):
    print(f"throttle test called: {arg}")

# def powerset(iterable):
#     """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
#     s = list(iterable)
#     return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))


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
    return f"{n:,}"


def call_github_action(
    action_name: str = None,
    params: Dict[str, Any] = None,
    ref="develop",
) -> Response:
    """Call a GitHub action

    This will work 'on' types of 'repository_dispatch' or 'workflow_dispatch'. Could not figure out a way to get params
    to work with 'repository_dispatch' (if it's even possible), so we use 'workflow_dispatch' for that.

    :param action_name:
    This can be an event_type (in case of repository_dispatch) or a filename (in case of workflow_dispatch).
    - repository_dispatch: event_type :Any .github/workflows/*.yml will have an EVENT_TYPE like so:
    ```yml
    on:
      repository_dispatch:
        types: [EVENT_TYPE]
    ```
    - workflow_dispatch: Use name of the filename in .github/workflows/, including the file extension.
    :param params: Any action 'inputs' to pass into the script. To see valid inputs, look at the
    workflow yaml. Only works with workflow_dispatch.
    :param ref: A reference, e.g. commit hash or branch, from which to run the action. For repository_dispatch, this
    is optional."""
    headers = {
        "Authorization": f"Bearer {CONFIG['personal_access_token']}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    push_type = (
        "workflow_dispatch"
        if action_name.endswith(".yaml") or action_name.endswith(".yml")
        else "repository_dispatch"
    )
    if push_type == "repository_dispatch" and params:
        raise ValueError(
            "Params only available with workflow_dispatch, not repository_dispatch."
        )
    if push_type == "repository_dispatch":
        url = "https://api.github.com/repos/jhu-bids/TermHub/dispatches"  # repository_dispatch
        payload = {"event_type": action_name}
        if ref:
            payload["client_payload"] = {"ref": ref}
    else:  # workflow_dispatch
        url = f"https://api.github.com/repos/jhu-bids/TermHub/actions/workflows/{action_name}/dispatches"
        payload = {"ref": ref}
        if params:
            payload["inputs"] = params

    response: Response = post(url, headers=headers, data=json.dumps(payload))
    if response.status_code >= 400:
        raise RuntimeError(
            f"Error calling GitHub action {action_name} with params:"
            f"\n{params}."
            f"\n\nResponse: {response.json()}")


def get_timer(name: str = "Timer", debug=False):
    """Get timer"""
    steps = []

    def step(msg: str = ""):
        """Step"""
        last_step = {}
        done = msg == "done"
        msg = f"{name} step {len(steps)+1} {msg}"
        t = datetime.now()
        i = None
        if len(steps):
            last_step = steps[-1]
            i = t - last_step["t"]
        steps.append({"msg": msg, "t": t, "i": i})
        if len(steps) > 1:
            print(f"{last_step['msg']} completed in {steps[-1]['i']}")
        if done:
            print(f"{name} completed in {(t - steps[0]['t'])}")
        if debug:
            for s in steps:
                print(", ".join([str(x) for x in s.values()]))

    return step


def cnt(vals):
    """Count values"""
    return len(set(vals))


def dump(o):
    """Return pretty printed json"""
    return json.dumps(o, indent=2)


def pdump(o):
    """Print pretty printed json"""
    print(dump(o))


def get_nested_from_dict(d: Dict, key_path: List):
    """Get nested value from dictionary"""
    return reduce(operator.getitem, key_path, d)


def return_err_with_trace(func):
    """Handle exceptions"""
    @wraps(func)
    async def decorated_func(*args, **kwargs):
        """Handle exceptions"""
        try:
            return await func(*args, **kwargs)
        except Exception as err:
            # stacktrace = "".join(traceback.format_exception(etype=type(err), value=err, tb=err.__traceback__))
            # getting error with above, @jflack4 fix this if my fix isn't what you wanted
            # noinspection PyTypeChecker not_sure_what_this_needs
            stacktrace = "".join(
                traceback.format_exception(err, value=err, tb=err.__traceback__)
            )
            warnings.warn(stacktrace)   # added so that we can see the stacktrace in the console and logs
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": str(err),
                    "stacktrace": stacktrace.split("\n"),
                },
            )

    return decorated_func


# Timeouts -------------------------------------------------------------------------------------------------------------
# todo: addresses https://github.com/jhu-bids/TermHub/issues/637
# async def disconnect_poller(request: Request, result: Any):
#     """
#     Poll for a disconnect.
#     If the request disconnects, stop polling and return.
#     """
#     try:
#         print("polling for disconnect")
#         while not await request.is_disconnected():
#             await asyncio.sleep(0.01)
#
#         print(f"Request disconnected: {request.url}")
#
#         return result
#     except asyncio.CancelledError as e:
#         print("Stopping polling loop")
#         raise e
#
#
# def cancel_on_disconnect(handler: Callable[[Request], Awaitable[Any]]):
#     """
#     Decorator that will check if the client disconnects,
#     and cancel the task if required.
#     """
#
#     @wraps(handler)
#     async def cancel_on_disconnect_decorator(request: Request, *args, **kwargs):
#         sentinel = object()
#
#         # Create two tasks, one to poll the request and check if the
#         # client disconnected, and another which is the request handler
#         poller_task = asyncio.ensure_future(disconnect_poller(request, sentinel))
#         handler_task = asyncio.ensure_future(handler(request, *args, **kwargs))
#
#         done, pending = await asyncio.wait(
#             [poller_task, handler_task], return_when=asyncio.FIRST_COMPLETED
#         )
#
#         # Cancel any outstanding tasks
#         for t in pending:
#             t.cancel()
#
#             try:
#                 await t
#             except asyncio.CancelledError:
#                 print(f"{t} was cancelled")
#             except Exception as exc:
#                 print(f"{t} raised {exc} when being cancelled")
#
#         # Return the result if the handler finished first
#         if handler_task in done:
#             return await handler_task
#
#         # Otherwise, raise an exception
#         # This is not exactly needed, but it will prevent
#         # validation errors if your request handler is supposed
#         # to return something.
#         print("Raising an HTTP error because I was disconnected!!")
#
#         raise HTTPException(503)
#
#     return cancel_on_disconnect_decorator
#
#
# @APP.get("/test-hangup")
# @cancel_on_disconnect
# async def test_hangup(
#     request: Request,
#     wait: float = Query(..., description="Time to wait, in seconds"),
# ):
#     """
#         test with http://localhost:8000/test-hangup?wait=5
#     """
#     try:
#         print(f"Sleeping for {wait:.2f}")
#
#         await asyncio.sleep(wait)
#
#         print("Sleep not cancelled")
#
#         return f"I waited for {wait:.2f}s and now this is the result"
#     except asyncio.CancelledError:
#         print("Exiting on cancellation")
#         return "I was cancelled"
