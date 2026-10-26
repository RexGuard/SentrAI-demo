"""Settings the portal reads, under SentrAI's new SENTRAI_* names or the old CACTAI_* ones.

SentrAI renamed its CACTAI_* settings to SENTRAI_* (PR #88). The portal shares a few of them with the
agent (the logs folder, the agent's key file), so it accepts either spelling; the new one wins.
"""
from __future__ import annotations

import os


def get(name: str, default: str | None = None) -> str | None:
    """SENTRAI_<name>, else CACTAI_<name>, else the default (empty values count as unset)."""
    for prefix in ("SENTRAI_", "CACTAI_"):
        value = os.environ.get(prefix + name)
        if value:
            return value
    return default
