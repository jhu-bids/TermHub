"""Backend utilities"""
import functools
import json
import operator
import os
import smtplib
import traceback
from functools import reduce
from typing import Any, Dict, List, Union
from datetime import datetime

import requests
from requests import Response
from starlette.responses import JSONResponse

from backend.db.config import CONFIG

JSON_TYPE = Union[Dict, List]


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
        if action_name.endswith(".yaml") or action_name.endswith(".yaml")
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

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response


def send_email(subject: str, body: str, to=["sigfried@sigfried.org", "jflack@jhu.edu"]):
    """Send email
    todo: Need alternative. Gmail doesn't work as of 2022/05:
     https://support.google.com/accounts/answer/6010255
     To help keep your account secure, from May 30, 2022,Google no longer supports the use of third-party apps or
     devices which ask you to sign in to your Google Account using only your username and password.
     - Alternative idea: Can populate a table and have a GitHub action read that table periodically and if it detects
     an unsent message, end in failure. This will trigger a 'failed action' email to be sent. We can open and read.
    """
    termhub_email_user = os.getenv("TERMHUB_EMAIL_USER")
    # create SMTP session
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    # server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    # login to SMTP server (not secure)
    server.login(termhub_email_user, os.getenv("TERMHUB_EMAIL_PASS"))
    # send email
    server.sendmail(termhub_email_user, to, f"Subject: {subject}\n\n{body}")
    server.quit()


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
            # stacktrace = "".join(traceback.format_exception(etype=type(err), value=err, tb=err.__traceback__))
            # getting error with above, @jflack4 fix this if my fix isn't what you wanted
            # noinspection PyTypeChecker not_sure_what_this_needs
            stacktrace = "".join(
                traceback.format_exception(err, value=err, tb=err.__traceback__)
            )
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": str(err),
                    "stacktrace": stacktrace.split("\n"),
                },
            )

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
