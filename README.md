# SentrAI demo lab

A safe place to watch [SentrAI](https://github.com/RexGuard/SentrAI) catch attacks live. This repo
holds only the demo: a fake student portal, harmless test attacks against it, and a page of buttons
for judges. SentrAI itself is never copied in here; the scripts check out the real product from its
own repo, so the product repo stays free of fake attacks.

```
fake portal :5000  --logs-->   SentrAI agent  --logs-->    SentrAI panel
(test attacks /lab) <--blocks--  "aegis-web"   <--blocks--  dashboard :8501
```

1. A button on `/lab` sends a short attack at the portal (from a made-up attacker address).
2. The portal writes it to its logs; SentrAI's **agent** on this machine sends them to the **panel**.
3. The panel scores the machine, opens incidents and decides on a block.
4. The agent picks the block up, and the portal starts showing that attacker the "Blocked by SentrAI" page.

## Start it

Needs Python 3.10+ and git.

**Windows (PowerShell):**

```powershell
.\demo.ps1            # first run takes a few minutes (gets SentrAI and its packages)
.\stop.ps1
```

**Linux / macOS:**

```bash
./demo.sh
./stop.sh
```

The first run prints a **dashboard setup code**. Open the dashboard (http://127.0.0.1:8501), create
the Owner account with it, and add the authenticator app it asks for. After that, sign in with that
account. Then open http://127.0.0.1:5000/lab next to the dashboard.

| Option (sh / ps1) | What it does |
|---|---|
| `--tripwires` / `-Tripwires` | Also the decoy admin page, bait rows and tarpit (the "Tripwires" button needs it) |
| `--fresh` / `-Fresh` | Start over: new panel data, new join, empty portal logs. Use between rehearsals |
| `--sentrai DIR` / `-SentrAI DIR` | Use this SentrAI checkout instead of the copy in `.demo/SentrAI` |
| `--panel URL --code CODE` / `-Panel URL -Code CODE` | Lab machine only: join a panel that runs on another computer (see below) |
| `--name NAME` / `-Name NAME` | This machine's name on the panel (default `aegis-web`) |
| `--speed 60` / `-Speed 60` | Faster panel timers (1 real minute = 1 hour). Default is real time |

Everything the demo makes stays in `.demo/` (its own SentrAI settings, database, logs and machine key),
so it never touches a real SentrAI install on the same computer. Delete `.demo/` to remove it all.

## The attacks

All of them only ever hit `127.0.0.1:5000` (the scripts refuse any other host), use addresses from the
documentation ranges (192.0.2.x, 198.51.100.x, 203.0.113.x), and never run a command or change real data.

| Button | Script | What the panel shows |
|---|---|---|
| Normal staff traffic | `python -m attacks.benign` | Stays green |
| Password guessing | `python -m attacks.brute_force` | Brute-force incident from 203.0.113.45. On its own it stays under the threshold, so a person approves the block (Approvals page) |
| SQL injection | `python -m attacks.sqli` | SQL-injection incident from 198.51.100.23 |
| Web shell (simulated) | `python -m attacks.shell` | Critical privilege-escalation incident from 198.51.100.77, waiting for a person on its own; after SQL injection it tips the machine over (see Full story) |
| Bulk data export | `python -m attacks.exfil` | Critical data-exfiltration incident; blocked on its own |
| Tripwires | `python -m attacks.spines` | Decoy page, planted password and bait rows: certain alerts, and the tarpit slows the intruder |
| **Full story** | `python scenario.py` | Normal traffic, password guessing nobody acts on, SQL injection, then a web shell from the same attacker: the machine passes its threshold and both attackers are blocked |

Run the scripts with the demo's Python (`.demo/venv/bin/python` or `.\.demo\venv\Scripts\python.exe`)
from this folder. Blocks last 2 hours (SentrAI's default); `--fresh` clears them for the next run.

## The AI intruder (three separate machines)

For the stage version: a **local, unrestricted AI model plays the intruder** against the website, with
SentrAI guarding it. Three machines, each on its own:

| Machine | Runs | Start it with |
|---|---|---|
| 1. **SentrAI panel** | The SentrAI panel and its dashboard (judges watch this) | `./demo.sh --panel-only --attacker-ip ATTACKER-IP` |
| 2. **Website** (the gateway) | The Aegis portal + SentrAI's agent, open to the network | the line machine 1 prints: `./demo.sh --panel http://PANEL-IP:8000 --allow-http --code CODE --listen` |
| 3. **AI attacker** | The local model and `attacker.py` | `python attacker.py --portal http://WEBSITE-IP:5000` |

(`demo.ps1` takes the same things as `-PanelOnly -AttackerIp`, `-Panel -AllowHttp -Code -Listen`.) Machine 1
prints the exact command for machine 2, including its one-time join code. Start them in that order; the
attacker last.

**The model.** `attacker.py` talks to any OpenAI-compatible endpoint, which local runners provide:
Ollama (`http://localhost:11434/v1`, the default), LM Studio, vLLM, llama.cpp. Pick the model with
`--model NAME` and `--model-url URL`. Pick one that supports tool calling (for Ollama, e.g. `llama3.1`,
`qwen2.5`, `mistral-nemo`). The intruder's instructions are in [`attacker/brief.md`](attacker/brief.md):
edit them to change its style or goals.

**What the AI can and cannot do.** It gets five moves (look at a page, try a login, search, bulk export, send
a command to the admin endpoint) and nothing else: no shell, no files, no other URLs
([`attacker/tools.py`](attacker/tools.py)). The portal runs nothing and holds only fake data. Before it
starts, the attacker checks that the address answers as *this* demo portal (a marker on `/healthz`) and is a
private/lab address; anything else is refused. So even an "unrestricted" model can only poke our own lab
portal, and one that tries other tools just gets "no such tool".

**What judges see.** On the panel: incidents open as the AI guesses passwords, injects the search box and
tries the admin endpoint; the machine's risk climbs past its threshold; SentrAI blocks the attacker's address.
On the attacker's terminal: its moves turn into `HTTP 403 [BLOCKED by SentrAI]`, and the model says so in its
after-action summary.

**Why `--attacker-ip`.** SentrAI never auto-blocks private-network addresses (the "attacker" could be a
colleague or a gateway), so on a LAN it would only ask a person to approve. `--attacker-ip` turns that
protection off on the demo panel so the AI machine can be blocked automatically. Use it in the lab only.
The panel runs over plain http here, so keep all three machines on a private test network.

**One computer, no real AI.** `python attacker.py` on the same machine as everything works the same way, and
the "Full story" button needs no model at all.

## Two computers (panel and lab apart)

On the panel's computer, run SentrAI normally and make a join code on its **Machines** page. On the lab
computer:

```bash
./demo.sh --panel https://panel.example.com:8000 --code ABCD-EFGH-JKLM
```

Add `--allow-http` (or `-AllowHttp`) only on a private test network without HTTPS. Without a local
panel, the demo starts just the agent and the portal.

## How blocks show up

The agent runs with `SENTRAI_FIREWALL=off`, so it changes no firewall rules on the demo laptop. It still
keeps the panel's block list in `.demo/agent.json`, and the portal refuses those addresses. To see real
firewall rules on a Linux lab machine, start with `SENTRAI_FIREWALL=auto SENTRAI_FIREWALL_ENFORCE=1`
(as root); the attacks' made-up addresses are what get blocked.

## Layout

```
demo.sh / demo.ps1     start everything            stop.sh / stop.ps1   stop it
agent_run.py           starts SentrAI's agent from the SentrAI checkout
attacker.py, attacker/ the AI intruder (its five moves, its brief, the model loop)
portal/                the fake Aegis Academy portal (Flask), its /lab page and tripwires
attacks/               the test attacks (localhost only)
scenario.py            the full story
seed/                  the portal's admin password and how many fake members to make
tests/                 pytest; test_sentrai_contract.py checks the portal's logs against SentrAI's
                       own collector when a SentrAI checkout is in .demo/SentrAI or SENTRAI_DIR
```

Tests: `.demo/venv/bin/python -m pytest -q tests` (CI runs them nightly against SentrAI main).

Aegis Academy is a fictional organization; all member data is synthetic.
