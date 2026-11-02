# SentrAI one-button demo site

A single self-contained page for the hackathon demo. Open `index.html` in any
browser (no server, no install, works offline) and press **Launch simulated
attack**.

It plays one workflow end to end on a fictional school portal, inside a copy of
the SentrAI Cybersecurity Control Panel as it looks today (Command Center, side
menu, Light Mode and Dark Mode):

1. **Spot** — a password-guessing burst hits the admin login from one address.
   A **Brute Force** risk card appears with *What happened* and *What it means*.
2. **Block** — risk passes 80 and SentrAI blocks the attacker on its own
   (there is no Auto Mode switch: SentrAI always acts) and slows every retry.
3. **Handled** — like the panel, a risk SentrAI already blocked leaves the
   active list and the counts. It sits under **Already handled by SentrAI**;
   opening it shows the suggested fix with *Keep the block* / *Undo the block*.
   Undoing puts it back on the active list (with *Block it again*).
4. **Talk to Sentry about this** — takes you to the main Sentry chat with this
   risk loaded and asks Sentry about it for you. Scripted plain-word answers.

The side menu hides with the button inside it. **Contact Us** at its bottom and
**What Sentry remembers** on the Sentry page open as dialogs whose backdrop
covers the whole page; both are demo stubs (nothing is sent or saved). The
theme and menu choice are remembered in the browser.

## Attacker window + the SentrAI panel (demo copy)

`attack.html` is the attacker's side, and it attacks the real panel's public demo copy
(https://rexguard.github.io/SentrAI/demo-copy/#/command):

1. Open the demo copy, then the attacker page, in the **same browser** (two windows, or one on the projector).
   The attacker page says "Connected to the SentrAI panel" when it finds it.
2. Press **Launch simulated attack**. A Critical **Brute Force** risk appears in the Command Center after a few
   seconds. SentrAI does **not** block it on its own here, so the attacker keeps trying.
3. Open it and press **Do the suggested fix**, as a manager would. The attacker's terminal shows it being blocked
   and giving up. (**Not a threat** closes it without blocking.)

The pages talk only inside the browser (BroadcastChannel, with a localStorage fallback); nothing goes over the
network. `index.html` (this folder) is the self-contained one-page version and no longer answers the attacker page.

## Online link

With GitHub Pages switched on for this repo (Settings > Pages > Deploy from a
branch, `main`, `/ (root)`), the page is at
https://rexguard.github.io/SentrAI-demo/ (which opens `demo-site/`), and the
attacker page is at https://rexguard.github.io/SentrAI-demo/demo-site/attack.html.

## It is a simulation

Nothing is really attacked. The page replays a scripted workflow using
synthetic accounts and documentation-only IP addresses (203.0.113.x, from
RFC 5737). It sends no real network traffic — it exists to *show* how SentrAI
responds.

For the full live lab (real contained attacks against a local portal, shipped
to the real SentrAI panel), see the kit at the repo root (`demo.sh` / `demo.ps1`
and `/lab`). This page is the simple, can't-fail version for showing one
workflow quickly.
