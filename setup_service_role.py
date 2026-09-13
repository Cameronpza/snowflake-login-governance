"""
One-off admin script: create a minimal, read-only role for CLAUDE_SERVICE_USER
and revoke its ACCOUNTADMIN grant.

Must be run with credentials whose current default role can grant/revoke
roles (e.g. ACCOUNTADMIN) - this deliberately ignores SNOWFLAKE_ROLE from
.env, since that variable is meant for the minimal dashboard role
(LOGIN_GOVERNANCE_READER) and won't have privilege to run this script,
especially on a fresh setup where that role doesn't exist yet.

Statements are mostly idempotent (CREATE ROLE IF NOT EXISTS, re-granting an
already-held privilege). The final REVOKE is not: re-running after
ACCOUNTADMIN has already been removed will fail there, which is expected.
Execution stops at the first failing statement, so a failed GRANT can never
be followed by the REVOKE.
"""
import os
import sys

from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")

STATEMENTS = [
    "CREATE ROLE IF NOT EXISTS LOGIN_GOVERNANCE_READER",
    "GRANT DATABASE ROLE SNOWFLAKE.SECURITY_VIEWER TO ROLE LOGIN_GOVERNANCE_READER",
    f"GRANT USAGE ON WAREHOUSE {WAREHOUSE} TO ROLE LOGIN_GOVERNANCE_READER",
    "GRANT ROLE LOGIN_GOVERNANCE_READER TO USER CLAUDE_SERVICE_USER",
    "ALTER USER CLAUDE_SERVICE_USER SET DEFAULT_ROLE = LOGIN_GOVERNANCE_READER",
    "REVOKE ROLE ACCOUNTADMIN FROM USER CLAUDE_SERVICE_USER",
]


def main():
    conn = snowflake.connector.connect(account=ACCOUNT, user=USER, password=PASSWORD)
    try:
        cur = conn.cursor()
        try:
            for stmt in STATEMENTS:
                print(f"\n=== {stmt} ===")
                cur.execute(stmt)
                for row in cur.fetchall():
                    print(row)
        finally:
            cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
