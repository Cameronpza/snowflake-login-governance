"""
One-off admin script: create a minimal, read-only role for CLAUDE_SERVICE_USER
and revoke its ACCOUNTADMIN grant.

Run with credentials that currently hold ACCOUNTADMIN (the service account
itself, today). Safe to re-run: every statement is idempotent.
"""
import os

from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE")

STATEMENTS = [
    "CREATE ROLE IF NOT EXISTS LOGIN_GOVERNANCE_READER",
    "GRANT DATABASE ROLE SNOWFLAKE.SECURITY_VIEWER TO ROLE LOGIN_GOVERNANCE_READER",
    "GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE LOGIN_GOVERNANCE_READER",
    "GRANT ROLE LOGIN_GOVERNANCE_READER TO USER CLAUDE_SERVICE_USER",
    "ALTER USER CLAUDE_SERVICE_USER SET DEFAULT_ROLE = LOGIN_GOVERNANCE_READER",
    "REVOKE ROLE ACCOUNTADMIN FROM USER CLAUDE_SERVICE_USER",
]


def main():
    conn_kwargs = dict(account=ACCOUNT, user=USER, password=PASSWORD)
    if ROLE:
        conn_kwargs["role"] = ROLE
    if WAREHOUSE:
        conn_kwargs["warehouse"] = WAREHOUSE

    conn = snowflake.connector.connect(**conn_kwargs)
    cur = conn.cursor()

    for stmt in STATEMENTS:
        print(f"\n=== {stmt} ===")
        try:
            cur.execute(stmt)
            for row in cur.fetchall():
                print(row)
        except Exception as e:
            print(f"ERROR: {e}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
