# SentrAI one-button demo site

A single self-contained page for the hackathon demo. Open `index.html` in any
browser (no server, no install, works offline) and press **Launch simulated
attack**.

It plays one workflow end to end on a fictional school portal, inside a copy of
the SentrAI panel as it looks today (Command Center, side menu, Light Mode and
Dark Mode):

1. **Spot** — a password-guessing burst hits the admin login from one address.
   A **Brute Force** risk card appears with *What happened* and *What it means*.
2. **Block** — risk passes 80 and SentrAI blocks the attacker on its own
   (there is no Auto Mode switch: SentrAI always acts) and slows every retry.
3. **Suggested fix** — the card shows the vetted fix wording, with
   *Keep the block* / *Undo the block*. The site never went down.
4. **Talk to Sentry** — the button on the card takes you to the main Sentry
   chat box with this risk loaded, where scripted plain-word answers explain it.
   *Back to the risk* (or Respond in the side menu) returns to the card.

The side menu hides with the button inside it, and the feedback form at its
bottom is a demo stub (nothing is sent). The theme and menu choice are
remembered in the browser.

## It is a simulation

Nothing is really attacked. The page replays a scripted workflow using
synthetic accounts and documentation-only IP addresses (203.0.113.x, from
RFC 5737). It sends no real network traffic — it exists to *show* how SentrAI
responds.

For the full live lab (real contained attacks against a local portal, shipped
to the real SentrAI panel), see the kit at the repo root (`demo.sh` / `demo.ps1`
and `/lab`). This page is the simple, can't-fail version for showing one
workflow quickly.
