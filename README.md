# Snowflake Login Governance Dashboard

🔗 **Live dashboard:** https://security-risk-dashboard2.streamlit.app/
📂 **Repository:** github.com/Cameronpza/snowflake-login-governance

A login/auth governance dashboard built against a real Snowflake account, using Snowflake's own `LOGIN\_HISTORY` data — a follow-up to my first project ([login-anomaly-detector](https://github.com/Cameronpza/login-anomaly-detector)), this time with real data, a fully agentic build process through Claude Code CLI, and a real security fix along the way.

\---

## What it does

The dashboard analyzes real login activity from my Snowflake trial account and surfaces three things:

1. **Repeated failed login bursts** — sliding-window detection (N failures within T minutes), plus automatic escalation flags for Snowflake's own `OVERFLOW\_FAILURE\_EVENTS\_ELIDED` and `USER\_LOCKED\_TEMP` events
2. **MFA compliance** — since every single login in this account uses no second authentication factor, this is presented as a standing compliance metric (overall and per-user MFA usage rate) rather than an anomaly alert, plus a separate tile tracking programmatic access token (PAT) logins
3. **Odd-hour logins** — a configurable business-hours window (default 08:00–18:00, timezone-adjustable), flagging activity outside normal working hours

All thresholds (excluded accounts, time window, failure count, business hours) are adjustable from the dashboard's sidebar rather than hardcoded, since the right values depend on real usage patterns that will keep evolving.

\---

## Why these specific detections — and why some ideas got dropped

Before building anything, I had Claude Code explore the actual real data first and draft a PRD (planning document) based on what it found — not what I assumed would be there. That surfaced some real limitations worth being upfront about:

* **A "weak auth anomaly" detector wasn't viable.** With 0% MFA usage across every row, there's no "normal" baseline to detect a deviation from — everyone looks the same. Rather than force a fake anomaly signal, I reframed this as a compliance metric instead, which is a more honest reflection of what the data actually supports.
* **A per-user learned "normal hours" baseline wasn't viable either**, given the limited number of active days and heavily test-skewed activity in a fresh trial account. I used a simple, static business-hours window instead — less sophisticated, but real and explainable, with the limitation documented rather than hidden.

This mirrors the same design philosophy as my first project: pick the honest, explainable option over one that looks more impressive but doesn't actually hold up against the real data.

\---

## The MCP journey (and why I ended up not using it here)

Part of this project's goal was connecting Claude Code to Snowflake using MCP (Model Context Protocol) — letting Claude Code query Snowflake conversationally during development. I tried three approaches, in order:

1. **Snowflake's own managed MCP server** — created successfully via SQL, but every connection attempt was rejected: this feature requires a paid Snowflake tier, not available on trial accounts.
2. **An open-source alternative** (`dynamike/snowflake-mcp-server`) — failed to build due to a missing C++ compiler dependency on Python 3.14. Fixed by pinning the tool's environment to Python 3.12 instead.
3. **The same tool, working, but with external-browser SSO authentication** — this timed out against Claude Code's MCP connection window, since browser-based login needs a human to complete it interactively within a short timeout.

After diagnosing all three, I made the call to connect via Snowflake's Python connector directly instead — a completely standard approach, just without the specific "ask Claude Code about my data conversationally" layer MCP would have added. Everything else (real data, CLI-driven build, PRD-based planning, security review) stayed intact.

\---

## A real security fix along the way

While exploring the account, I noticed the service account used for this project (`claude\_service\_user`) had been given full `ACCOUNTADMIN` privileges — far more than it needed just to read login history. I had Claude Code design and apply a proper least-privilege fix:

* Created a new role, `LOGIN\_GOVERNANCE\_READER`, using Snowflake's built-in `SECURITY\_VIEWER` database role (scoped read access to security-relevant views only, not the entire account)
* Granted only the warehouse `USAGE` needed to run queries
* Revoked `ACCOUNTADMIN` from the service account entirely
* **Verified the fix actually worked** — rather than just trusting the grant/revoke statements succeeded, I deliberately tried a privileged operation (`USE ROLE ACCOUNTADMIN`) afterward and confirmed it correctly failed

This dashboard now runs entirely on that minimal, read-only role.

\---

## How this was built

This entire project — from exploring the real data, to drafting the PRD, to writing the SQL, to building the dashboard, to designing and verifying the security fix — was built through **Claude Code CLI**, working directly in my terminal rather than a chat interface. A `/security-review` was run against the finished codebase (no high or medium confidence findings — confirmed parameterized queries throughout, no credential leakage, no unsafe input handling). A separate multi-agent review (`/ultrareview`) caught and fixed several real bugs before anything shipped, including a scenario where a partially-failed permission change could have left the service account stranded with no valid role at all.

\---

## Tech used

* **Snowflake** — real trial account, `SNOWFLAKE.ACCOUNT\_USAGE.LOGIN\_HISTORY`
* **Python + snowflake-connector-python** — direct database connection
* **Streamlit** — dashboard, deployed on Streamlit Community Cloud
* **Claude Code CLI** — the entire build process, agentically

\---

## Project structure

```
├── SQL/                          # numbered exploration + detection queries
├── app.py                        # Streamlit dashboard
├── explore.py                    # initial data exploration script
├── setup\_service\_role.py         # one-off script: creates the least-privilege role
├── PRD.md                        # planning document, written before building
├── .env.example                  # template for required environment variables
└── notes.txt                     # working notes from building this project
```

\---

## What I'd do next

* Revisit MCP once either a paid Snowflake tier or a non-interactive auth method (key-pair) is set up, to add conversational data exploration back in
* Expand the odd-hours detection to a per-user learned baseline once there's enough real, organic usage data to support one
* Add automated alerting instead of a dashboard you have to check manually

