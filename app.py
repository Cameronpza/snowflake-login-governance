"""
Snowflake Login Governance Dashboard.

Surfaces the three MVP detections from PRD.md against real LOGIN_HISTORY
data, pulled via the read-only LOGIN_GOVERNANCE_READER role:
  1. Repeated failed logins (burst + Snowflake-escalated events)
  2. MFA compliance tile + programmatic-access-token tile
  3. Odd-hour logins (static business-hours window, a coarse heuristic)

Run with: streamlit run app.py
"""
import os
from pathlib import Path

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SQL_DIR = Path(__file__).parent / "SQL"
DEFAULT_EXCLUDED_USERS = ["CLAUDE_SERVICE_USER", "TESTUSER1", "TESTUSER2"]

st.set_page_config(page_title="Login Governance", layout="wide")


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
    )


def read_statements(filename):
    """Split a SQL file into individual statements, dropping comment-only chunks."""
    text = (SQL_DIR / filename).read_text()
    statements = []
    for chunk in text.split(";"):
        code_lines = [line for line in chunk.splitlines() if not line.strip().startswith("--")]
        if any(line.strip() for line in code_lines):
            statements.append(chunk.strip())
    return statements


@st.cache_data(ttl=300)
def run_file(filename, params):
    """Execute every statement in a SQL file, returning one DataFrame per statement."""
    cur = get_connection().cursor()
    try:
        frames = []
        for statement in read_statements(filename):
            cur.execute(statement, params)
            cols = [c[0] for c in cur.description]
            frames.append(pd.DataFrame(cur.fetchall(), columns=cols))
        return frames
    finally:
        cur.close()


st.title("Snowflake Login Governance")
st.caption("SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY, queried via LOGIN_GOVERNANCE_READER")

with st.sidebar:
    st.header("Config")
    exclude_noise = st.checkbox("Exclude test/service accounts", value=True)
    excluded_users = DEFAULT_EXCLUDED_USERS if exclude_noise else []
    st.caption(f"Excluded: {', '.join(excluded_users) if excluded_users else 'none'}")

    st.subheader("Repeated failed logins")
    threshold = st.number_input("Failure threshold (N)", min_value=1, value=5)
    window_minutes = st.number_input("Sliding window, minutes (T)", min_value=1, value=10)

    st.subheader("Odd-hours window")
    timezone = st.text_input("Timezone", value="UTC")
    business_start, business_end = st.slider("Business hours", 0, 24, (8, 18))

params = {
    "excluded_users": excluded_users or ["__NONE__"],
    "window_minutes": int(window_minutes),
    "threshold": int(threshold),
    "timezone": timezone,
    "business_start_hour": int(business_start),
    "business_end_hour": int(business_end),
}

# --- Detection 1: Repeated failed logins ---------------------------------
st.header("1. Repeated Failed Logins")
st.caption(
    f"Flags a failed login when the same user has ≥ {threshold} failures within "
    f"{window_minutes} minutes, or Snowflake already escalated it (overflow/lockout)."
)
(failed_logins,) = run_file("06_repeated_failed_logins.sql", params)
st.metric("Flagged events", len(failed_logins))
st.dataframe(failed_logins, use_container_width=True)

# --- Detection 2: MFA compliance + programmatic access tokens ------------
st.header("2. Weak Auth / MFA Compliance")
overall_mfa, per_user_mfa, pat_usage = run_file("07_mfa_compliance.sql", params)

st.subheader("MFA compliance")
st.caption("Standing compliance tile, not an anomaly flag — see PRD Detection 2.")
mfa_pct = overall_mfa["MFA_PCT"].iloc[0] if len(overall_mfa) else 0
st.metric("Logins with a second factor", f"{mfa_pct}%")
st.dataframe(per_user_mfa, use_container_width=True)

st.subheader("Programmatic access tokens")
st.caption("Separate risk category from password logins — long-lived token exposure.")
st.metric("Total PAT logins", int(pat_usage["PAT_LOGINS"].sum()) if len(pat_usage) else 0)
st.dataframe(pat_usage, use_container_width=True)

# --- Detection 3: Odd-hour logins -----------------------------------------
st.header("3. Odd-Hour Logins")
st.caption(
    f"Static {business_start:02d}:00–{business_end:02d}:00 ({timezone}) window — "
    "a coarse heuristic, not personalized anomaly detection. See PRD Detection 3."
)
(odd_hours,) = run_file("08_odd_hours.sql", params)
st.metric("Flagged events", len(odd_hours))
st.dataframe(odd_hours, use_container_width=True)
