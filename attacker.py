"""Point a local AI model at the demo portal as the intruder, so judges watch SentrAI catch it.

The portal, the SentrAI panel and this AI attacker can each be on their own machine (the
three-machine demo). This script only needs to reach the portal's web address; it never touches the
panel or any other machine, and the AI's moves can only hit that one portal.

Examples:
    # same machine as the portal (the simplest demo)
    python attacker.py

    # the AI attacker on its own machine, portal on another box on the LAN
    python attacker.py --portal http://192.168.1.50:5000

    # choose the local model / endpoint (default: Ollama's llama3.1 on localhost)
    python attacker.py --model llama3.1 --model-url http://localhost:11434/v1

The model talks over an OpenAI-compatible API (Ollama, LM Studio, vLLM, llama.cpp, or a hosted one).
"""
from __future__ import annotations

import argparse
import os
import sys

from attacker import agent, tools


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AI intruder vs. the SentrAI demo portal")
    ap.add_argument("--portal", default=os.environ.get("ATTACKER_PORTAL", "http://127.0.0.1:5000"),
                    help="the demo portal's web address (default http://127.0.0.1:5000)")
    ap.add_argument("--model", default=os.environ.get("ATTACKER_MODEL", "llama3.1"),
                    help="the local model's name (default llama3.1)")
    ap.add_argument("--model-url", default=os.environ.get("ATTACKER_BASE_URL", "http://localhost:11434/v1"),
                    help="the model's OpenAI-compatible endpoint (default http://localhost:11434/v1)")
    ap.add_argument("--src-ip", default=os.environ.get("ATTACKER_SRC_IP", "203.0.113.200"),
                    help="the made-up attacker address stamped on the traffic")
    ap.add_argument("--steps", type=int, default=20, help="most moves the model may make")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between moves (nicer to watch)")
    ap.add_argument("--i-own-this", action="store_true",
                    help="allow a non-private portal address (only if you are certain it is your lab)")
    args = ap.parse_args(argv)

    try:
        portal = tools.Portal(args.portal, src_ip=args.src_ip, i_own_this=args.i_own_this)
    except tools.NotTheDemoPortal as exc:
        print(f"[attacker] refusing to start: {exc}", file=sys.stderr)
        return 2
    try:
        agent.run(portal, args.model_url, args.model, os.environ.get("ATTACKER_API_KEY", ""),
                  max_steps=args.steps, delay=args.delay)
    except agent.ModelError as exc:
        print(f"[attacker] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[attacker] stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
