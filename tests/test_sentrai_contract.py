"""The portal's logs read the way SentrAI's own collector expects (the agent runs that collector).

Needs a SentrAI checkout: SENTRAI_DIR, or the copy demo.sh / demo.ps1 put in .demo/SentrAI.
Skipped without one.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from portal import create_app, paths, spines

KIT_DIR = Path(__file__).resolve().parents[1]
SENTRAI = Path(os.environ.get("SENTRAI_DIR") or KIT_DIR / ".demo" / "SentrAI")
if not (SENTRAI / "mvp" / "lab" / "collector").is_dir():
    pytest.skip(f"no SentrAI checkout at {SENTRAI} (set SENTRAI_DIR)", allow_module_level=True)
sys.path.insert(1, str(SENTRAI / "mvp" / "lab"))
collector = pytest.importorskip("collector.collector")

ATTACKER = {"X-Demo-Src-IP": "203.0.113.99"}


def _log(name: str) -> list[dict]:
    log = paths.logs_dir() / name
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture(autouse=True)
def _clean():
    for name in paths.ALL_LOGS:
        (paths.logs_dir() / name).unlink(missing_ok=True)
    yield
    create_app(spines_on=False)


def test_same_log_names_as_the_collector():
    from collector import paths as sentrai_paths

    assert paths.ALL_LOGS == sentrai_paths.ALL_LOGS


def test_attack_lines_become_events():
    c = create_app().test_client()
    c.post("/login", data={"user": "admin", "password": "nope"}, headers=ATTACKER)
    c.get("/search", query_string={"q": "\' OR \'1\'=\'1"}, headers=ATTACKER)
    c.get("/admin/run", query_string={"cmd": "whoami"}, headers=ATTACKER)
    for name, layer in ((paths.AUTH_LOG, "web"), (paths.DB_LOG, "db"), (paths.OS_LOG, "os")):
        events = [collector.normalize(name, r) for r in _log(name)]
        assert events and all(e["layer"] == layer and e["src_ip"] == "203.0.113.99" for e in events), name


def test_collector_ships_spine_events_with_their_layer():
    c = create_app(spines_on=True).test_client()
    c.get("/export", headers=ATTACKER)
    c.get(spines.HONEYPOT_PATH, headers=ATTACKER)
    events = [collector.normalize(paths.DECEPTION_LOG, r) for r in _log(paths.DECEPTION_LOG)]
    assert [(e["layer"], e["source"]) for e in events] == [("db", "tripwire"), ("web", "tripwire")]
    assert events[0]["asset_criticality"] == 1.5
    assert events[0]["raw"].startswith("tripwire honeytoken_row:")
