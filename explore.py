"""
Direct Snowflake exploration for login-governance data.
Connects with snowflake-connector-python using credentials from .env
(no MCP involved).
"""
import os
import sys

from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
ROLE = os.environ.get("SNOWFLAKE_ROLE")
WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE")


def run(cur, sql, label):
    print(f"\n=== {label} ===")
    try:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        print(" | ".join(cols))
        for row in rows:
            print(" | ".join(str(v) for v in row))
        if not rows:
            print("(no rows)")
    except Exception as e:
        print(f"ERROR: {e}")


def main():
    conn_kwargs = dict(account=ACCOUNT, user=USER, password=PASSWORD)
    if ROLE:
        conn_kwargs["role"] = ROLE
    if WAREHOUSE:
        conn_kwargs["warehouse"] = WAREHOUSE

    conn = snowflake.connector.connect(**conn_kwargs)
    try:
        cur = conn.cursor()
        try:
            run(cur, "SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()", "Session info")
            run(
                cur,
                """
                SELECT EVENT_TIMESTAMP, USER_NAME, CLIENT_IP, REPORTED_CLIENT_TYPE,
                       FIRST_AUTHENTICATION_FACTOR, IS_SUCCESS, ERROR_MESSAGE
                FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
                ORDER BY EVENT_TIMESTAMP DESC
                LIMIT 25
                """,
                "Recent login history (ACCOUNT_USAGE)",
            )
        finally:
            cur.close()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
