"""The only things the AI intruder can do: a handful of moves against one demo portal, nothing else.

Each tool makes one request to the fake Aegis portal and returns a short, readable result. There is
no "run shell", "read file" or "open any URL" tool, so whatever the model decides, it can only poke
the one portal the demo is about. The portal executes nothing and holds only synthetic data.

The portal may be on this machine or another on the LAN (the three-machine demo), so the target is
given as an address rather than pinned to localhost. Before any attack the address is checked: it
must answer /healthz as our demo portal ("demo_portal": "sentrai-aegis-lab"), and it must be a
private/loopback address unless --i-own-this is passed. A public address is refused outright. This
keeps an "unrestricted" local model from being turned on anything but our own lab portal.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attacks import _common  # noqa: E402  (shared attacker session + headers)

MAX_TEXT = 1200       # how much page text the model gets back, so one /export can't flood the context
DEMO_MARKER = "sentrai-aegis-lab"


class NotTheDemoPortal(RuntimeError):
    """The target did not prove it is our fictional lab portal, or is a public address."""


def _clip(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + " …(truncated)"


def _is_private(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    addrs = {info[4][0] for info in infos}
    return bool(addrs) and all(
        ipaddress.ip_address(a).is_private or ipaddress.ip_address(a).is_loopback for a in addrs
    )


def verify_target(base: str, i_own_this: bool = False, get: Callable[..., Any] = requests.get) -> str:
    """Return the portal's base URL once it proves it is our demo portal, else raise.

    * The host must be private/loopback, unless i_own_this says the operator vouches for it.
    * /healthz must answer with our demo marker, so a wrong address can never be attacked.
    """
    base = (base or "").rstrip("/")
    host = urlparse(base).hostname or ""
    if not host:
        raise NotTheDemoPortal(f"not a usable portal address: {base!r}")
    if not i_own_this and not _is_private(host):
        raise NotTheDemoPortal(
            f"{host} is not a private/lab address. The AI attacker only runs against the demo portal "
            f"on your own network; pass --i-own-this only if you are certain this is your lab portal.")
    try:
        data = get(f"{base}/healthz", timeout=5).json()
    except (requests.RequestException, ValueError) as exc:
        raise NotTheDemoPortal(f"{base} did not answer as the demo portal (/healthz): {exc}") from exc
    if data.get("demo_portal") != DEMO_MARKER:
        raise NotTheDemoPortal(f"{base} is not the SentrAI demo portal (no demo marker on /healthz).")
    return base


class Portal:
    """A session pinned to one verified demo portal, under one made-up attacker address."""

    def __init__(self, base: str, src_ip: str = "203.0.113.200", i_own_this: bool = False):
        self.base = verify_target(base, i_own_this)
        self.sess = _common.make_session(src_ip)
        self.src_ip = src_ip

    def _result(self, r, extra: str = "") -> dict[str, Any]:
        out = {"status": r.status_code, "blocked": r.status_code == 403, "body": _clip(r.text)}
        if extra:
            out["note"] = extra
        return out

    def look(self, path: str = "/") -> dict[str, Any]:
        """GET a path on the portal (e.g. /, /robots.txt, /admin-legacy). Reconnaissance."""
        if not path.startswith("/"):
            path = "/" + path
        return self._result(self.sess.get(f"{self.base}{path}", timeout=5))

    def login(self, user: str, password: str) -> dict[str, Any]:
        """Try the staff login with a username and password."""
        r = self.sess.post(f"{self.base}/login", data={"user": user, "password": password}, timeout=5)
        return self._result(r, "signed in" if r.status_code == 200 else "rejected")

    def search(self, query: str) -> dict[str, Any]:
        """Search the member directory (the field an injection payload would go in)."""
        return self._result(self.sess.get(f"{self.base}/search", params={"q": query}, timeout=5))

    def export(self) -> dict[str, Any]:
        """Pull the whole member list at once (bulk data grab)."""
        return self._result(self.sess.get(f"{self.base}/export", timeout=5))

    def run_command(self, cmd: str) -> dict[str, Any]:
        """Send a command to the portal's admin endpoint. It is only logged, never executed."""
        r = self.sess.get(f"{self.base}/admin/run", params={"cmd": cmd}, timeout=5)
        return self._result(r, "the portal simulates this endpoint and runs nothing")


# name -> (description for the model, parameter names). The agent turns these into the model's tools.
TOOLS: dict[str, tuple[str, list[str]]] = {
    "look": ("Fetch a page on the portal to see what is there. Good first move: '/', '/robots.txt'.", ["path"]),
    "login": ("Attempt the staff login with a username and password.", ["user", "password"]),
    "search": ("Search the member directory; the query is passed straight through.", ["query"]),
    "export": ("Download the entire member list in one request.", []),
    "run_command": ("Ask the portal's admin endpoint to run a shell command (simulated).", ["cmd"]),
}


def dispatch(portal: Portal, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run one tool the model picked. Unknown tools and bad arguments come back as a plain error."""
    fn: Callable[..., dict[str, Any]] | None = getattr(portal, name, None)
    if name not in TOOLS or fn is None:
        return {"error": f"no such tool {name!r}; tools are {sorted(TOOLS)}"}
    try:
        return fn(**{k: args[k] for k in TOOLS[name][1] if k in args})
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:  # a network blip shouldn't crash the demo
        return {"error": f"{name} failed: {exc.__class__.__name__}: {exc}"}
