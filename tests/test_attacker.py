"""The AI intruder: its tools only touch the demo portal, and the agent loop drives them."""
from __future__ import annotations

import json

import pytest

from attacker import agent, tools
from portal import create_app


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status
    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_verify_refuses_a_public_address():
    with pytest.raises(tools.NotTheDemoPortal):
        tools.verify_target("http://93.184.216.34:5000", get=lambda *a, **k: _Resp({"demo_portal": "x"}))


def test_verify_refuses_a_private_address_without_the_marker():
    with pytest.raises(tools.NotTheDemoPortal):
        tools.verify_target("http://127.0.0.1:5000", get=lambda *a, **k: _Resp({"ok": True}))


def test_verify_accepts_the_demo_portal():
    base = tools.verify_target("http://127.0.0.1:5000/",
                               get=lambda *a, **k: _Resp({"demo_portal": tools.DEMO_MARKER}))
    assert base == "http://127.0.0.1:5000"


def test_i_own_this_allows_a_non_private_address_that_still_proves_itself():
    base = tools.verify_target("http://example-lab.test:5000", i_own_this=True,
                               get=lambda *a, **k: _Resp({"demo_portal": tools.DEMO_MARKER}))
    assert base.endswith(":5000")


def _portal_on_the_test_client():
    """A tools.Portal whose requests go to the Flask test client, not the network."""
    client = create_app().test_client()
    p = tools.Portal.__new__(tools.Portal)
    p.base, p.src_ip = "", "203.0.113.200"
    class S:
        def get(self, url, params=None, timeout=None):
            return _ClientResp(client.get(url, query_string=params, headers={"X-Demo-Src-IP": p.src_ip}))
        def post(self, url, data=None, timeout=None):
            return _ClientResp(client.post(url, data=data, headers={"X-Demo-Src-IP": p.src_ip}))
    p.sess = S()
    return p


class _ClientResp:
    def __init__(self, r):
        self.status_code = r.status_code
        self.text = r.get_data(as_text=True)


def test_tools_only_expose_the_portal_moves():
    p = _portal_on_the_test_client()
    assert tools.dispatch(p, "login", {"user": "admin", "password": "nope"})["status"] == 401
    assert tools.dispatch(p, "export", {})["status"] == 200
    assert "error" in tools.dispatch(p, "read_file", {"path": "/etc/passwd"})  # no such tool


def test_agent_runs_the_moves_the_model_asks_for():
    p = _portal_on_the_test_client()
    scripted = [
        {"role": "assistant", "content": "Trying the search box.",
         "tool_calls": [{"id": "1", "function": {"name": "search", "arguments": json.dumps({"query": "' OR '1'='1"})}}]},
        {"role": "assistant", "content": "Pulling the list.",
         "tool_calls": [{"id": "2", "function": {"name": "export", "arguments": "{}"}}]},
        {"role": "assistant", "content": "Done."},  # no tool_calls -> loop ends
    ]
    calls = iter(scripted)
    out = []
    agent.run(p, "http://model", "fake", ask=lambda *a, **k: next(calls), say=out.append, delay=0)
    log = "\n".join(out)
    assert "search(" in log and "export(" in log and "the model stopped" in log
