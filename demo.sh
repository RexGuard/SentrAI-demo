#!/usr/bin/env bash
# Starts the SentrAI demo lab on Linux or macOS (the bash twin of demo.ps1).
#
#   panel   SentrAI's own core + dashboard, from a SentrAI checkout     http://127.0.0.1:8000 / :8501
#   agent   SentrAI's machine agent, joined to the panel as "aegis-web": ships the portal's logs
#           and keeps the panel's blocks for this machine
#   portal  the fake Aegis Academy student portal                     http://127.0.0.1:5000
#           with the test-attack buttons on                           http://127.0.0.1:5000/lab
#
# Everything the demo makes stays in .demo/ (its own SentrAI settings, logs, keys), so it never
# touches a real SentrAI install on the same computer. Stop it all with ./stop.sh.
#
#   ./demo.sh                          everything on this computer (panel, agent, portal)
#   ./demo.sh --tripwires              also the decoy admin page, bait rows and tarpit
#   ./demo.sh --sentrai ~/SentrAI      use this SentrAI checkout instead of cloning one into .demo/
#   ./demo.sh --panel https://panel.example.com:8000 --code ABCD-EFGH-JKLM
#                                      lab machine only: join a panel running elsewhere with a join
#                                      code from its Machines page (add --allow-http on a private
#                                      test network without HTTPS)
#   ./demo.sh --panel-only --attacker-ip 192.168.1.60
#                                      three-machine demo, machine 1: only the SentrAI panel. The attacker's
#                                      address is the one allowed to be blocked (private networks are
#                                      otherwise never auto-blocked)
#   ./demo.sh --panel https://PANEL:8000 --code CODE --listen
#                                      machine 2: the website (portal) + agent, open to the network so the
#                                      AI attacker machine can reach it on port 5000
#                                      machine 3: python attacker.py --portal http://PORTAL-IP:5000
#   ./demo.sh --name web-02            the lab machine's name on the panel (default aegis-web)
#   ./demo.sh --speed 60               faster panel timers (1 real minute = 1 hour); default real time
#   ./demo.sh --fresh                  start over: new panel data, new join, empty portal logs (keeps the
#                                      SentrAI copy and the Python packages)
#   ./demo.sh --no-dashboard --no-browser
#
# Needs python3 with venv and git (Debian/Ubuntu: sudo apt install python3-venv git).
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$KIT/.demo"
PYTHON="${PYTHON:-python3}"
SENTRAI="${SENTRAI_DIR:-}"
SENTRAI_REPO="${SENTRAI_REPO:-https://github.com/RexGuard/SentrAI}"
SENTRAI_BRANCH="${SENTRAI_BRANCH:-main}"
PANEL=""
CODE=""
ALLOW_HTTP=0
NAME="aegis-web"
TRIPWIRES=0
PANEL_ONLY=0
LISTEN_ALL=0
ATTACKER_IP=""
SPEED="${DEMO_SPEED:-1}"
RUN_FLAGS=()
FRESH=0
while [ $# -gt 0 ]; do
    case "$1" in
        --sentrai) SENTRAI="$2"; shift 2 ;;
        --panel) PANEL="$2"; shift 2 ;;
        --code) CODE="$2"; shift 2 ;;
        --allow-http) ALLOW_HTTP=1; shift ;;
        --name) NAME="$2"; shift 2 ;;
        --tripwires|--spines) TRIPWIRES=1; shift ;;
        --panel-only) PANEL_ONLY=1; shift ;;
        --listen) LISTEN_ALL=1; shift ;;
        --attacker-ip) ATTACKER_IP="$2"; shift 2 ;;
        --speed) SPEED="$2"; shift 2 ;;
        --no-dashboard|--no-browser) RUN_FLAGS+=("$1"); shift ;;
        --fresh) FRESH=1; shift ;;
        -h|--help) sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1 (see --help)" >&2; exit 2 ;;
    esac
done
if [ -n "$PANEL" ] && [ -z "$CODE" ] && [ ! -f "$STATE/agent.json" ]; then
    echo "--panel needs --code: make a join code on the panel's Machines page." >&2; exit 2
fi
if [ -f "$STATE/pids" ]; then
    echo "The demo seems to be running already (found .demo/pids). Run ./stop.sh first." >&2; exit 1
fi
if "$PYTHON" -c "import socket; socket.create_connection(('127.0.0.1', 5000), timeout=1)" 2>/dev/null; then
    echo "Port 5000 (the portal's) is already in use: stop whatever runs there first." >&2; exit 1
fi
if [ "$FRESH" = 1 ]; then
    echo "Starting over: removing the demo's panel data, agent key and portal logs ..."
    rm -rf "$STATE/panel" "$STATE/agent" "$STATE/logs" "$STATE/agent.json" "$STATE/portal.sqlite3"
fi
mkdir -p "$STATE/logs" "$STATE/agent" "$STATE/panel"
rm -f "$STATE/panel/started"

# 1. SentrAI itself: the product is never copied into this repo, only checked out next to it.
if [ -z "$SENTRAI" ]; then
    SENTRAI="$STATE/SentrAI"
    if [ -d "$SENTRAI/.git" ]; then
        echo "Updating SentrAI ($SENTRAI_BRANCH) in .demo/SentrAI ..."
        git -C "$SENTRAI" pull -q --ff-only origin "$SENTRAI_BRANCH" || echo "  (could not update; using the copy there)"
    else
        echo "Getting SentrAI ($SENTRAI_BRANCH) into .demo/SentrAI ..."
        git clone -q --depth 1 --branch "$SENTRAI_BRANCH" "$SENTRAI_REPO" "$SENTRAI"
    fi
fi
SENTRAI="$(cd "$SENTRAI" && pwd)"
MVP="$SENTRAI/mvp"
echo "$SENTRAI" > "$STATE/sentrai-dir"
[ -f "$MVP/lab/agent/agent.py" ] || { echo "$SENTRAI has no machine agent (mvp/lab/agent): use a newer SentrAI." >&2; exit 1; }

# 2. The portal's own Python packages.
if [ ! -x "$STATE/venv/bin/python" ]; then
    echo "Creating the portal's venv ..."
    "$PYTHON" -m venv "$STATE/venv"
fi
"$STATE/venv/bin/python" -m pip install -q -r "$KIT/requirements.txt"
PY_KIT="$STATE/venv/bin/python"

PIDS=()
save_pids() { printf '%s\n' "${PIDS[@]}" > "$STATE/pids"; }
start_bg() {  # name command...
    local name="$1"; shift
    local SETSID=""; command -v setsid >/dev/null 2>&1 && SETSID=setsid
    ( exec $SETSID "$@" ) >"$STATE/$name.log" 2>&1 < /dev/null &
    PIDS+=("$!"); save_pids
    printf '  started %-7s (pid %s, log .demo/%s.log)\n' "$name" "$!" "$name"
}
wait_http() {  # url [seconds]
    local deadline=$(( $(date +%s) + ${2:-40} ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        "$PY_KIT" -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)" "$1" 2>/dev/null && return 0
        sleep 0.5
    done
    return 1
}

# 3. The panel, unless this machine joins one elsewhere. It runs in host scope so each machine
#    has its own risk score and its own blocks, with its settings kept in .demo/panel.
if [ -z "$PANEL" ]; then
    export SENTRAI_CONFIG="$STATE/panel/config.json" SENTRAI_RISK_SCOPE=host DEMO_SPEED="$SPEED"
    export SENTRAI_SCOUT_SOURCES="$STATE/panel/sources.json"
    # The panel's database, machine keys, backups and quarantine also stay in .demo/panel, never in
    # the SentrAI checkout (which may be a real install when --sentrai points at one).
    export SENTRAI_DB="$STATE/panel/data/sentrai.db" SENTRAI_QUARANTINE="$STATE/panel/data/quarantine"
    mkdir -p "$STATE/panel/data"
    if [ ! -f "$STATE/panel/sign-in.txt" ]; then
        # Makes the panel's settings file (so SentrAI's first-run questions are skipped) and the
        # dashboard's first sign-in (a one-time Owner setup code, or a password on older SentrAI),
        # kept here because it is shown only once.
        "$PY_KIT" "$MVP/sentrai_config.py" admin --email judge@sentrai-demo.local > "$STATE/panel/sign-in.txt"
    fi
    BIND=()
    if [ "$PANEL_ONLY" = 1 ]; then
        BIND=(--core-bind 0.0.0.0)  # the website machine's agent reaches the panel over the network
        # SentrAI never auto-blocks private-network addresses (the "attacker" could be a colleague or
        # a gateway). In this lab the AI attacker is on the LAN, so allow blocking that one address.
        if [ -n "$ATTACKER_IP" ]; then
            export PROTECTED_NETS=off
            export PROTECTED_IPS="127.0.0.1,::1,localhost"
        else
            echo "Note: no --attacker-ip given, so SentrAI will only ask a person to approve blocks from LAN addresses." >&2
        fi
    fi
    echo "Starting the SentrAI panel ..."
    "$MVP/run.sh" --speed "$SPEED" ${BIND[@]+"${BIND[@]}"} ${RUN_FLAGS[@]+"${RUN_FLAGS[@]}"} > "$STATE/panel.log" 2>&1 \
        || { cat "$STATE/panel.log"; echo "The panel did not start (see above)." >&2; exit 1; }
    echo "local" > "$STATE/panel/started"
    PANEL="http://127.0.0.1:${SENTRAI_CORE_PORT:-8000}"
    ALLOW_HTTP=1
    unset PROTECTED_NETS PROTECTED_IPS
    wait_http "$PANEL/health" || { echo "The panel is not answering on $PANEL (see $MVP/.run_logs/core.log)." >&2; exit 1; }
    TOKEN="$("$PY_KIT" "$MVP/sentrai_config.py" token | tail -n 1)"
    unset SENTRAI_CONFIG SENTRAI_SCOUT_SOURCES SENTRAI_DB SENTRAI_QUARANTINE
    if [ "$PANEL_ONLY" = 1 ] || [ ! -f "$STATE/agent.json" ] || ! grep -q "\"$PANEL\"" "$STATE/agent.json"; then
        CODE="$("$PY_KIT" - "$PANEL" "$TOKEN" "$NAME" <<'EOF'
import json, sys, urllib.request
panel, token, name = sys.argv[1:4]
req = urllib.request.Request(f"{panel}/fleet/join-codes", method="POST",
                             data=json.dumps({"operator": "demo", "name": name}).encode(),
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=10))["code"])
EOF
)"
    fi
fi

if [ "$PANEL_ONLY" = 1 ]; then
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"; LAN_IP="${LAN_IP:-THIS-PANEL-IP}"
    echo
    echo "SentrAI panel is running for the three-machine demo."
    echo "  Dashboard:  http://$LAN_IP:${SENTRAI_DASHBOARD_PORT:-8501}   (it listens on this computer only; open it here)"
    sed 's/^ */  /' "$STATE/panel/sign-in.txt"
    echo
    echo "  On the WEBSITE machine run:"
    echo "    ./demo.sh --panel http://$LAN_IP:${SENTRAI_CORE_PORT:-8000} --allow-http --code $CODE --listen"
    echo "  On the AI ATTACKER machine run:"
    echo "    python attacker.py --portal http://WEBSITE-MACHINE-IP:5000"
    [ -n "$ATTACKER_IP" ] || echo "  (restart this with --attacker-ip THE-ATTACKER-MACHINE-IP so SentrAI may block it)"
    echo "  The join code works once and lasts 24 hours. Stop with ./stop.sh"
    exit 0
fi

# 4. The agent: its own settings, key file and collector place, reading only the portal's logs.
export SENTRAI_CONFIG="$STATE/agent/config.json"
export SENTRAI_AGENT_FILE="$STATE/agent.json"
export SENTRAI_COLLECTOR_STATE="$STATE/agent/collector-state.json"
export SENTRAI_SCOUT_SOURCES="$STATE/agent/sources.json"
export SENTRAI_LAB_LOGS="$STATE/logs"
export SENTRAI_FIREWALL="${SENTRAI_FIREWALL:-off}"  # blocks show on the portal; no firewall rules on the demo laptop
export PYTHONUNBUFFERED=1 PYTHONUTF8=1
if [ ! -x "$MVP/lab/.venv/bin/python" ]; then
    echo "Creating the agent's venv ..."
    "$PYTHON" -m venv "$MVP/lab/.venv"
    "$MVP/lab/.venv/bin/python" -m pip install -q -r "$MVP/lab/requirements.txt"
fi
PY_AGENT="$MVP/lab/.venv/bin/python"
if [ -n "$CODE" ]; then
    rm -f "$STATE/agent.json" "$SENTRAI_COLLECTOR_STATE"
    join=(join --panel "$PANEL" --code "$CODE" --name "$NAME")
    [ "$ALLOW_HTTP" = 1 ] && join+=(--allow-http)
    "$PY_AGENT" "$KIT/agent_run.py" "$SENTRAI" "${join[@]}"
fi
echo "Starting the agent and the portal ..."
start_bg agent "$PY_AGENT" "$KIT/agent_run.py" "$SENTRAI" run

# 5. The portal.
[ "$TRIPWIRES" = 1 ] && export SENTRAI_SPINES=1
[ "$LISTEN_ALL" = 1 ] && export PORTAL_HOST=0.0.0.0
cd "$KIT"
start_bg portal "$PY_KIT" -m portal
wait_http "http://127.0.0.1:5000/healthz" 20 || echo "The portal is not answering yet (see .demo/portal.log)." >&2

echo
echo "SentrAI demo lab is running."
if [ -f "$STATE/panel/started" ] && [[ " ${RUN_FLAGS[*]-} " != *" --no-dashboard "* ]]; then
    echo "  Panel dashboard: http://127.0.0.1:${SENTRAI_DASHBOARD_PORT:-8501}"
    sed 's/^ */  /' "$STATE/panel/sign-in.txt"
    echo "  (shown on every start; once the Owner account exists, sign in with it. If the code ran out:"
    echo "   SENTRAI_CONFIG=.demo/panel/config.json python3 .demo/SentrAI/mvp/sentrai_config.py admin)"
else
    echo "  Panel:           $PANEL  (dashboard of the panel's machine)"
fi
echo "  Portal:          http://127.0.0.1:5000        (this machine is \"$NAME\" on the panel)"
if [ "$LISTEN_ALL" = 1 ]; then
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "  Open to the network: http://${LAN_IP:-THIS-MACHINE-IP}:5000  <- point the AI attacker here"
fi
echo "  Test attacks:    http://127.0.0.1:5000/lab    or: $PY_KIT scenario.py"
echo "  Stop everything: ./stop.sh"
