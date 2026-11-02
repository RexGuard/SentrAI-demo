# SentrAI one-button demo site

A single self-contained page for the hackathon demo. Open `index.html` in any
browser (no server, no install, works offline) and press **Launch simulated
attack**.

It plays one workflow end to end on a fictional school portal:

1. **Detect** — a password-guessing burst hits the admin login from one address.
2. **Explain** — SentrAI describes the risk in plain words for the owner.
3. **Block** — risk crosses the machine's threshold; SentrAI blocks the
   attacker and slows (tarpits) every retry.
4. **Resolve** — the attacker is locked out, the incident is closed and the
   record is saved. The site never went down.

## It is a simulation

Nothing is really attacked. The page replays a scripted workflow using
synthetic accounts and documentation-only IP addresses (203.0.113.x, from
RFC 5737). It sends no real network traffic — it exists to *show* how SentrAI
responds.

For the full live lab (real contained attacks against a local portal, shipped
to the real SentrAI panel), see the kit at the repo root (`demo.sh` / `demo.ps1`
and `/lab`). This page is the simple, can't-fail version for showing one
workflow quickly.
