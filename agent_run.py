"""Starts SentrAI's agent for the demo portal: ``python agent_run.py <SentrAI dir> join|run|status ...``.

The agent itself is SentrAI's (``mvp/lab/agent``); this only finds it in the given checkout and,
for ``run``, names the portal's log lines after the machine the agent joined as. Older SentrAI
versions sealed them as ``web-01`` while the panel stamped the joined name, which read as a
false "log tampering" alert (fixed in SentrAI PR #73); setting the name here keeps the demo
clean on either version.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    lab = Path(sys.argv[1]).resolve() / "mvp" / "lab"
    if not (lab / "agent" / "agent.py").is_file():
        print(f"no SentrAI agent in {lab} (is this a SentrAI checkout from after the central panel?)", file=sys.stderr)
        return 2
    sys.path.insert(0, str(lab))
    from agent import agent  # noqa: E402  (SentrAI's agent)

    args = sys.argv[2:]
    if args[:1] == ["run"]:
        name = agent.load().get("host")
        if name:
            from collector import collector

            # the setting's name depends on the SentrAI version (renamed in SentrAI PR #88)
            os.environ["SENTRAI_HOST" if (lab.parent / "sentrai_config.py").is_file() else "CACTAI_HOST"] = name
            collector.HOST = name
    return agent.main(args)


if __name__ == "__main__":
    sys.exit(main())
