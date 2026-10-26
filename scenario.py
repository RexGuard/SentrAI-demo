"""Full SentrAI demo story against the demo portal on this machine.

Order: benign baseline -> brute force -> pause -> SQL injection -> web shell.
Prints narration between phases so it can drive the recording.

Start the lab first (./demo.sh or .\demo.ps1): the portal on :5000 and the SentrAI agent
that ships its logs to the panel. The "Full story" button on http://127.0.0.1:5000/lab runs
this same script.

Run:
    python scenario.py
    python scenario.py --pause 6 --host 127.0.0.1
    python scenario.py --tripwires   # adds the tripwires phase (lab started with --tripwires)
"""
from __future__ import annotations

import argparse
import time

from attacks import benign, brute_force, shell, spines, sqli


def narrate(text: str) -> None:
    print()
    print("~" * 62)
    print(f"  {text}")
    print("~" * 62)


def countdown(seconds: float, why: str) -> None:
    print(f"\n  [pause] {why} ({seconds:.0f}s)…")
    time.sleep(seconds)


def main() -> None:
    ap = argparse.ArgumentParser(description="SentrAI live demo scenario")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--pause", type=float, default=6.0,
                    help="seconds to wait after brute force (operator 'ignores' it)")
    ap.add_argument("--tripwires", "--spines", dest="spines", action="store_true",
                    help="add phase 6: an intruder touches the honeypot and honeytokens (tarpit slows them)")
    args = ap.parse_args()
    h, p = args.host, args.port

    narrate("PHASE 1 — Baseline. Normal staff traffic. Dashboard should stay green.")
    benign.run(h, p, count=6, delay=0.5, src_ip="192.0.2.10")

    narrate("PHASE 2 — Brute force on the admin login (attacker 203.0.113.45). "
            "Risk should jump to Amber and an incident should open.")
    brute_force.run(h, p, count=12, delay=0.3, src_ip="203.0.113.45")

    narrate("PHASE 3 — Operator IGNORES the alert. The inaction penalty ticks the "
            "gauge upward while nobody acts.")
    countdown(args.pause, "letting the inaction penalty accrue")

    narrate("PHASE 4 — SQL injection on /search (attacker 198.51.100.23). "
            "Risk climbs into the red, just under the machine's threshold.")
    sqli.run(h, p, count=6, delay=0.4, src_ip="198.51.100.23")

    narrate("PHASE 5 — The same attacker tries to run commands through a web shell "
            "(simulated: nothing runs). Risk passes the threshold and SentrAI blocks "
            "every attacker on this machine on its own.")
    shell.run(h, p, count=3, delay=0.5, src_ip="198.51.100.23")

    if args.spines:
        narrate("PHASE 6 — Tripwires. A third intruder (203.0.113.99) finds the decoy admin page, "
                "reuses its planted password and dumps the bait rows. Each touch is a certain alert, "
                "and the tarpit slows every request after the first.")
        spines.run(h, p, delay=0.3, src_ip="203.0.113.99")

    narrate("SCENARIO COMPLETE — check the dashboard for the incident queue, the "
            "risk gauge, the evidence report and the audit chain.")


if __name__ == "__main__":
    main()
