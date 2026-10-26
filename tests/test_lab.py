"""/lab: the test-attack buttons, and who may claim a made-up attacker address."""
from __future__ import annotations

import json
import time

from portal import create_app, lab, paths
from portal.blocklist import blocklist, read_once


def test_lab_page_lists_every_attack():
    c = create_app().test_client()
    page = c.get("/lab").get_data(as_text=True)
    for key, (title, _, _) in lab.ATTACKS.items():
        assert title in page and f'data-attack="{key}"' in page


def test_unknown_attack_is_refused():
    c = create_app().test_client()
    assert c.post("/lab/run/rm-rf").status_code == 404


def test_lab_is_never_blocked():
    blocklist.update(ips=["127.0.0.1"])
    try:
        assert create_app().test_client().get("/lab").status_code == 200
    finally:
        blocklist.update(ips=[])


def test_runner_runs_one_attack_at_a_time(monkeypatch):
    monkeypatch.setitem(lab.ATTACKS, "sleepy", ("Sleepy", "", ["-c", "import time; print('hi'); time.sleep(1)"]))
    r = lab.Runner()
    assert r.start("sleepy") and not r.start("sleepy")
    deadline = time.time() + 10
    while r.status()["running"] and time.time() < deadline:
        time.sleep(0.05)
    assert r.status()["lines"] == ["hi"] and r.start("sleepy")


def test_demo_address_header_only_from_this_machine():
    c = create_app().test_client()
    c.get("/", headers={"X-Demo-Src-IP": "203.0.113.5"}, environ_base={"REMOTE_ADDR": "10.1.2.3"})
    c.get("/", headers={"X-Demo-Src-IP": "203.0.113.6"})
    lines = (paths.logs_dir() / paths.ACCESS_LOG).read_text(encoding="utf-8").splitlines()
    ips = [json.loads(line)["src_ip"] for line in lines[-2:]]
    assert ips == ["10.1.2.3", "203.0.113.6"]


def test_blocks_come_from_the_agent_file(tmp_path):
    f = tmp_path / "agent.json"
    f.write_text(json.dumps({"host": "aegis-web", "blocked": ["203.0.113.45"]}))
    assert read_once(f) and blocklist.is_blocked("203.0.113.45", None)
    f.write_text("not json")
    assert not read_once(f) and blocklist.is_blocked("203.0.113.45", None)  # fail open: keep, never add
    blocklist.update(ips=[])
