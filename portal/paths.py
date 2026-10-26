"""Where the demo portal keeps its logs, seed data and database.

Everything defaults to folders inside this kit, so nothing touches the SentrAI install it
reports to. The agent on this machine is pointed at the same logs folder (SENTRAI_LAB_LOGS),
which is how the portal's activity reaches the central panel.

  SENTRAI_LAB_LOGS   JSON-lines logs the agent ships   (default: <kit>/.demo/logs)
  SENTRAI_LAB_DB    SQLite file with the fake members  (default: <kit>/.demo/portal.sqlite3)
  SENTRAI_LAB_SEED  admin password + member count      (default: <kit>/seed)
  SENTRAI_AGENT_FILE the agent's file; its "blocked" list is what the portal refuses
                    (default: <kit>/.demo/agent.json)
"""
from __future__ import annotations

import os
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = KIT_DIR / ".demo"


def env(name: str, default: str | None = None) -> str | None:
    """SENTRAI_<name>, or the old CACTAI_<name> from before SentrAI's rename."""
    return os.environ.get(f"SENTRAI_{name}") or os.environ.get(f"CACTAI_{name}") or default


def _dir_from_env(name: str, default: Path) -> Path:
    value = env(name)
    path = Path(value) if value else default
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    """Directory holding the JSON-lines log files."""
    return _dir_from_env("LAB_LOGS", STATE_DIR / "logs")


def seed_dir() -> Path:
    return _dir_from_env("LAB_SEED", KIT_DIR / "seed")


def db_path() -> Path:
    value = env("LAB_DB")
    p = Path(value) if value else STATE_DIR / "portal.sqlite3"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def agent_file() -> Path:
    value = env("AGENT_FILE")
    return Path(value) if value else STATE_DIR / "agent.json"


# Log file names: the same ones SentrAI's collector looks for (mvp/lab/collector/paths.py).
ACCESS_LOG = env("LOG_ACCESS", "access.jsonl")
AUTH_LOG = env("LOG_AUTH", "auth.jsonl")
DB_LOG = env("LOG_DB", "db.jsonl")
OS_LOG = env("LOG_OS", "os.jsonl")
DECEPTION_LOG = env("LOG_DECEPTION", "deception.jsonl")  # tripwires (spines.py)

ALL_LOGS = (ACCESS_LOG, AUTH_LOG, DB_LOG, OS_LOG, DECEPTION_LOG)
