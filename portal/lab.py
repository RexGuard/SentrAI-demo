"""``/lab``: the test-attack buttons for judges.

Each button runs one of this kit's attack scripts (``attacks/``) in a separate process, against
this portal only (the scripts refuse any host but localhost:5000). The page shows the script's
output as it runs, so the audience sees the attack while the central panel catches it.
One attack runs at a time.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time

from flask import Blueprint, abort, jsonify, render_template, request

from . import paths

bp = Blueprint("lab", __name__)


@bp.before_request
def _this_machine_only():
    """The buttons run attacks from here, so only someone at this computer may press them, even when the
    portal itself is open to the network for the AI attacker machine."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        abort(404)

# button -> (title, what the panel should show, command after "python")
ATTACKS: dict[str, tuple[str, str, list[str]]] = {
    "benign": ("Normal staff traffic", "Stays green: logins and searches by a staff member.",
               ["-m", "attacks.benign"]),
    "brute_force": ("Password guessing", "12 wrong admin passwords from 203.0.113.45: an incident a person approves the block for.",
                    ["-m", "attacks.brute_force"]),
    "sqli": ("SQL injection", "Injection payloads on the search box from 198.51.100.23: risk passes the threshold and SentrAI blocks on its own.",
             ["-m", "attacks.sqli"]),
    "shell": ("Web shell (simulated)", "Commands sent to a fake admin endpoint from 198.51.100.77: a critical incident. Nothing runs.",
              ["-m", "attacks.shell"]),
    "exfil": ("Bulk data export", "The whole member list pulled again and again from 203.0.113.77: SentrAI blocks on its own.",
              ["-m", "attacks.exfil"]),
    "tripwires": ("Tripwires", "An intruder finds the decoy admin page and the bait rows (portal started with tripwires on).",
                  ["-m", "attacks.spines"]),
    "story": ("Full story", "Normal traffic, password guessing nobody acts on, SQL injection, then a web shell: SentrAI blocks both attackers.",
              ["scenario.py"]),
}


class Runner:
    """At most one attack process at a time, with its output kept for the page."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.name: str | None = None
        self.lines: list[str] = []
        self.running = False
        self.started = 0.0

    def start(self, name: str) -> bool:
        with self.lock:
            if self.running:
                return False
            self.name, self.lines, self.running, self.started = name, [], True, time.time()
        threading.Thread(target=self._run, args=(ATTACKS[name][2],), daemon=True).start()
        return True

    def _run(self, args: list[str]) -> None:
        try:
            proc = subprocess.Popen([sys.executable, "-u", *args], cwd=paths.KIT_DIR, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:  # type: ignore[union-attr]
                with self.lock:
                    self.lines.append(line.rstrip())
                    del self.lines[:-400]
            proc.wait()
        except OSError as exc:
            with self.lock:
                self.lines.append(f"could not start the attack: {exc}")
        finally:
            with self.lock:
                self.running = False

    def status(self) -> dict:
        with self.lock:
            return {"name": self.name, "running": self.running, "lines": list(self.lines),
                    "title": ATTACKS[self.name][0] if self.name else None}


runner = Runner()


@bp.get("/lab")
def lab_page():
    return render_template("lab.html", attacks=ATTACKS)


@bp.post("/lab/run/<name>")
def lab_run(name: str):
    if name not in ATTACKS:
        return jsonify(ok=False, error="unknown attack"), 404
    if not runner.start(name):
        return jsonify(ok=False, error="another attack is still running"), 409
    return jsonify(ok=True)


@bp.get("/lab/status")
def lab_status():
    from .blocklist import blocklist

    return jsonify(**runner.status(), blocked=blocklist.snapshot()["ips"], agent_seen=blocklist.agent_seen)
