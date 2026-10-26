#!/usr/bin/env bash
# Stops what ./demo.sh started: the portal, the agent and (when it started one) the local panel.
set -uo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$KIT/.demo"
if [ -f "$STATE/pids" ]; then
    while read -r pid; do
        [ -n "$pid" ] || continue
        kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null && echo "  stopped pid $pid"
    done < "$STATE/pids"
    rm -f "$STATE/pids"
fi
if [ -f "$STATE/panel/started" ] && [ -f "$STATE/sentrai-dir" ]; then
    MVP="$(cat "$STATE/sentrai-dir")/mvp"
    [ -x "$MVP/stop.sh" ] && "$MVP/stop.sh"
    rm -f "$STATE/panel/started"
fi
echo "Demo lab stopped. Its data stays in .demo/ (delete that folder for a fresh start)."
