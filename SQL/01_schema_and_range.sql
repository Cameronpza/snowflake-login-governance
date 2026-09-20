-- Understand what LOGIN_HISTORY actually contains before designing detections:
-- full column list, row count, and the date range we have to work with.

DESCRIBE TABLE SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY;

SELECT
    COUNT(*)                    AS total_rows,
    MIN(EVENT_TIMESTAMP)        AS earliest_event,
    MAX(EVENT_TIMESTAMP)        AS latest_event,
    COUNT(DISTINCT USER_NAME)   AS distinct_users,
    COUNT(DISTINCT CLIENT_IP)   AS distinct_ips
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY;
