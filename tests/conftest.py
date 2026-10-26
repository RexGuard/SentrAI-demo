"""Pytest configuration: isolate logs/DB/agent file into a temp dir and fix sys.path."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_DIR))

# Redirect all file output to a throwaway temp directory BEFORE the portal resolves any paths.
_TMP = tempfile.mkdtemp(prefix="sentrai-demo-test-")
os.environ.setdefault("SENTRAI_LAB_LOGS", str(Path(_TMP) / "logs"))
os.environ.setdefault("SENTRAI_LAB_DB", str(Path(_TMP) / "portal.sqlite3"))
os.environ.setdefault("SENTRAI_AGENT_FILE", str(Path(_TMP) / "agent.json"))
# Keep the real seed dir (holds the admin password) — do not override it.
