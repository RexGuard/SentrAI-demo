"""Containment on the portal: it refuses the addresses the SentrAI agent on this machine blocked.

The panel decides; the agent fetches this machine's block list and keeps it in its own file
(``blocked`` in agent.json), whether it is also writing firewall rules or only in dry run. The
portal reads that file every 2 seconds, so a judge sees the block land on the attacked machine
itself. If the file is missing or unreadable the portal *fails open*: a broken demo never locks
out normal traffic.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from . import paths


class Blocklist:
    """Thread-safe snapshot of contained IPs / users."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ips: set[str] = set()
        self._users: set[str] = set()
        self.last_ok: float | None = None
        self.agent_seen: bool = False

    def update(self, ips=None, users=None) -> None:
        with self._lock:
            self._ips = set(ips or [])
            self._users = set(users or [])

    def is_blocked(self, ip: str | None, user: str | None) -> bool:
        with self._lock:
            if ip and ip in self._ips:
                return True
            if user and user in self._users:
                return True
            return False

    def snapshot(self) -> dict:
        with self._lock:
            return {"ips": sorted(self._ips), "users": sorted(self._users)}


# Process-wide instance shared by the Flask app and the poller.
blocklist = Blocklist()


def read_once(path: Path | None = None) -> bool:
    """Load the agent's current blocks once. Returns True if the agent file was readable."""
    path = path or paths.agent_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Fail open: keep what we had, but only an explicit entry ever blocks.
        blocklist.agent_seen = False
        return False
    blocklist.update(ips=data.get("blocked", []))
    blocklist.last_ok = time.time()
    blocklist.agent_seen = True
    return True


def start_poller(interval: float = 2.0) -> threading.Thread:
    """Start the background reader (daemon thread)."""

    def _loop() -> None:
        while True:
            read_once()
            time.sleep(interval)

    t = threading.Thread(target=_loop, name="blocklist-reader", daemon=True)
    t.start()
    return t
