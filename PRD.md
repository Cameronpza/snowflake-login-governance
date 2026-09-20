# PRD: Snowflake Login Governance Dashboard

**Status: Ready to build.** Open questions from the first draft are
resolved below (MFA tile framing, odd-hours window); remaining items are
config values to set at build time, not blockers.

## Goal

Give an account owner visibility into login behavior on this Snowflake
account, covering three detection areas: weak auth usage, repeated failed
logins, and odd-hour logins. Built against real `LOGIN_HISTORY` data pulled
via the read-only `LOGIN_GOVERNANCE_READER` role (see `SQL/01`-`05` and
`notes.txt` for the raw exploration).

## Data source

`SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY`. As of 2026-09-17:

| | |
|---|---|
| Total rows | 39 |
| Date range | 2026-09-10 to 2026-09-17 (4 distinct active days) |
| Distinct users | 4 (1 real human, 2 test accounts, 1 service account) |
| Distinct source IPs | 1 real IP + 1 placeholder (`0.0.0.0`) |
| Success / fail | 26 / 13 |

`ACCOUNT_USAGE` views have up to 3 hours of latency and ~1 year retention;
neither matters yet at this volume, but the dashboard should be built
assuming both will matter later.

**Known noise in the current data:** `CLAUDE_SERVICE_USER` (6 rows) is this
exploration and prior script runs, not a real login to govern. `TESTUSER1`
and `TESTUSER2` (19 rows combined) are manually-generated test activity.
Recommend the dashboard support excluding a configurable list of
service/test accounts, since right now they're roughly half the dataset.

---

## Detection 1: Repeated failed logins — well supported

Real signal exists. On 2026-09-12, `TESTUSER1` had 6 failed attempts and
`TESTUSER2` had 4, in short succession, including one `USER_LOCKED_TEMP`
result and one `OVERFLOW_FAILURE_EVENTS_ELIDED` row (Snowflake's own marker
that it collapsed additional failures beyond what it recorded — the real
burst was larger than the row count shows).

**Proposed logic:**
- Sliding window: flag when a single `USER_NAME` has ≥ N failed
  (`IS_SUCCESS = 'NO'`) events within T minutes. Start with N=5 / T=10 as a
  baseline, tune once more history exists.
- Treat `OVERFLOW_FAILURE_EVENTS_ELIDED` as an automatic high-severity flag
  regardless of count — it means Snowflake itself decided the burst was
  large enough to stop logging individually.
- Surface `USER_LOCKED_TEMP` as its own "already escalated by Snowflake"
  indicator, separate from the raw count, since it's a stronger signal than
  the threshold heuristic.
- Group by `ERROR_CODE`/`ERROR_MESSAGE` so the dashboard can distinguish
  "wrong password" bursts from expired-password or network-policy blocks,
  which need different follow-up.

## Detection 2: Weak auth usage — DECIDED: compliance tile, not an anomaly flag

`SECOND_AUTHENTICATION_FACTOR` is `NULL` on all 39 rows — every login in
this account, successful or not, is single-factor. `LOGIN_DETAILS`,
`CONNECTION`, and `AUTHORIZING_INTEGRATION_NAME` are empty/null throughout,
so there's no secondary signal hiding elsewhere in the row.

An anomaly detector needs a baseline of "normal" to compare against. With
0% MFA usage across every user and every day observed, there is no
variation to key an anomaly off — "this login lacked MFA" would fire on
literally every row, which isn't a detection, it's just the account's
current state.

**Decision:** ship this as a **standing compliance tile** — overall MFA
usage rate ("X% of logins in the last N days had a second factor"), broken
out by user — not an event-level alert. It becomes a real anomaly detector
automatically once MFA adoption is non-zero and a per-user baseline can
form; no rework needed then, just add the alerting rule on top of the same
underlying metric.

Separately worth surfacing: `CAMZA`'s 6 `PROGRAMMATIC_ACCESS_TOKEN` logins
are a different risk category from password logins (long-lived token
exposure vs. credential guessing) and probably deserve their own tile
rather than being lumped into "weak auth."

## Detection 3: Odd-hour logins — DECIDED: static business-hours window

This is the one to be honest about upfront, same as the unusual-access
flag on the last project.

- Activity clusters entirely in a ~8-hour UTC band (08:00-16:00) across
  only 4 calendar days, and skews weekend-heavy (Sat 24, Sun 11, Thu 4 —
  no Mon/Tue/Wed/Fri activity at all). That's consistent with this being
  manually-triggered test/exploration activity, not a real usage pattern
  to baseline against.
- Per-user event counts (14, 12, 7, 6) are far too low to fit a reliable
  per-user statistical baseline (e.g., mean/stddev of login hour) — with
  single digits to low teens of data points, any such model is fitting
  noise, and it will only have "night owl" tester activity to learn from,
  not real behavior.
- There's also no timezone-normalization story yet: all analysis above
  used UTC hour, but "odd hours" is inherently about the user's local
  working hours, which this data doesn't tell us.

**Decision:** given the limited and skewed data, skip the per-user learned
baseline entirely (not just for now — it's not a reasonable model for this
account size). Ship a **static, account-wide window: flag logins outside
08:00-18:00**. Treat the window's timezone as a config value — the
exploration above used UTC, but the account owner should set this to
whatever timezone actually reflects working hours before launch (see open
questions). Label the tile clearly as a coarse heuristic, not personalized
anomaly detection, so it isn't mistaken for something it isn't.

## Data limitations summary (things the current data can't support)

- **Odd-hour anomaly detection** (per-user baseline): insufficient
  history and volume — resolved via the static-window decision in
  Detection 3, not by waiting for more data.
- **IP/geo-based checks** (new location, impossible travel): only one real
  source IP across all users and all rows; not requested for this PRD but
  worth flagging now so it isn't assumed to be a quick follow-on — it needs
  IP diversity that doesn't exist yet. Out of scope for this build.
- **MFA-as-anomaly**: 0% adoption account-wide means no baseline to deviate
  from — resolved via the compliance-tile decision in Detection 2.

## MVP scope

1. Repeated-failed-logins detector (threshold + overflow/lockout escalation).
2. MFA/weak-auth compliance tile (usage rate, broken out by user) +
   separate programmatic-access-token tile.
3. Odd-hours tile using the static 08:00-18:00 window (timezone
   configurable), labeled as a coarse heuristic.
4. Config: excludable service/test account list, applied account-wide.

## Open questions (config, not blockers)

- Should service/test accounts (`CLAUDE_SERVICE_USER`, `TESTUSER*`) be
  filtered out entirely, or shown in a separate "non-production" section?
- What timezone should the 08:00-18:00 odd-hours window use for this
  account?
- What failure threshold/window (N/T) matches real tolerance here, versus
  the 5-per-10-minutes starting guess?
