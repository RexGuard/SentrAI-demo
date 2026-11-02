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

## Online link

With GitHub Pages switched on for this repo (Settings > Pages > Deploy from a
branch, `main`, `/ (root)`), the page is at
https://rexguard.github.io/SentrAI-demo/ (which opens `demo-site/`).

## It is a simulation

Nothing is really attacked. The page replays a scripted workflow using
synthetic accounts and documentation-only IP addresses (203.0.113.x, from
RFC 5737). It sends no real network traffic — it exists to *show* how SentrAI
responds.

For the full live lab (real contained attacks against a local portal, shipped
to the real SentrAI panel), see the kit at the repo root (`demo.sh` / `demo.ps1`
and `/lab`). This page is the simple, can't-fail version for showing one
workflow quickly.
