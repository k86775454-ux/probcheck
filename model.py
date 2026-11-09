"""One model call, with a simulated model by default.

Environment (never write these into a file or commit them):
    IIS_MODEL      "mock" (default) or "http"
    IIS_MODEL_URL  an OpenAI-compatible chat-completions endpoint
    IIS_MODEL_NAME model name sent with the request, if the endpoint needs one
    IIS_API_KEY    your own key

The live route is wired but has not been evaluated in this project: all reported results use the mock.
"""
import json
import os
import urllib.request

MODE = os.environ.get("IIS_MODEL", "mock")
ENDPOINT = os.environ.get("IIS_MODEL_URL", "")
NAME = os.environ.get("IIS_MODEL_NAME", "")
KEY = os.environ.get("IIS_API_KEY", "")


def live():
    return MODE == "http" and bool(ENDPOINT and KEY)


def call(messages, schema=None, timeout=20, overclaim=False):
    """Return the model's reply as text. Falls back to the mock whenever the live route is not configured."""
    if not live():
        import mock_model
        return mock_model.call(messages, schema, overclaim=overclaim)
    body = {"messages": messages, "temperature": 0}
    if NAME:
        body["model"] = NAME
    if schema:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.loads(r.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def call_json(messages, schema, timeout=20, overclaim=False):
    """Return a dict, or None if the reply was not valid JSON. None is a caught error, not a crash."""
    try:
        text = call(messages, schema, timeout, overclaim=overclaim)
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, OSError, KeyError, ValueError):
        return None
