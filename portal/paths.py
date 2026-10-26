"""Where the demo portal keeps its logs, seed data and database.

Everything defaults to folders inside this kit, so nothing touches the SentrAI install it
reports to. The agent on this machine is pointed at the same logs folder (CACTAI_LAB_LOGS),
which is how the portal's activity reaches the central panel.

  CACTAI_LAB_LOGS   JSON-lines logs the agent ships   (default: <kit>/.demo/logs)
  CACTAI_LAB_DB     SQLite file with the fake members  (default: <kit>/.demo/portal.sqlite3)
  CACTAI_LAB_SEED   admin password + member count      (default: <kit>/seed)
  CACTAI_AGENT_FILE the agent's file; its "blocked" list is what the portal refuses
                    (default: <kit>/.demo/agent.json)
"""
from __future__ import annotations

import os
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = KIT_DIR / ".demo"


def _dir_from_env(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    path = Path(value) if value else default
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    """Directory holding the JSON-lines log files."""
    return _dir_from_env("CACTAI_LAB_LOGS", STATE_DIR / "logs")


def seed_dir() -> Path:
    return _dir_from_env("CACTAI_LAB_SEED", KIT_DIR / "seed")


def db_path() -> Path:
    value = os.environ.get("CACTAI_LAB_DB")
    p = Path(value) if value else STATE_DIR / "portal.sqlite3"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def agent_file() -> Path:
    value = os.environ.get("CACTAI_AGENT_FILE")
    return Path(value) if value else STATE_DIR / "agent.json"


# Log file names: the same ones SentrAI's collector looks for (mvp/lab/collector/paths.py).
ACCESS_LOG = os.environ.get("CACTAI_LOG_ACCESS", "access.jsonl")
AUTH_LOG = os.environ.get("CACTAI_LOG_AUTH", "auth.jsonl")
DB_LOG = os.environ.get("CACTAI_LOG_DB", "db.jsonl")
OS_LOG = os.environ.get("CACTAI_LOG_OS", "os.jsonl")
DECEPTION_LOG = os.environ.get("CACTAI_LOG_DECEPTION", "deception.jsonl")  # tripwires (spines.py)

ALL_LOGS = (ACCESS_LOG, AUTH_LOG, DB_LOG, OS_LOG, DECEPTION_LOG)
