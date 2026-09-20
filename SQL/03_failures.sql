-- Failure volume and reasons -- needed for the "repeated failed logins" detection.

SELECT
    IS_SUCCESS,
    COUNT(*) AS attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY IS_SUCCESS;

SELECT
    ERROR_CODE,
    ERROR_MESSAGE,
    COUNT(*) AS attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE IS_SUCCESS = 'NO'
GROUP BY ERROR_CODE, ERROR_MESSAGE
ORDER BY attempts DESC;

-- Per-user, per-day failure counts -- is there ever a real burst, or just one-offs?
SELECT
    USER_NAME,
    DATE_TRUNC('day', EVENT_TIMESTAMP) AS day,
    COUNT(*) AS failed_attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE IS_SUCCESS = 'NO'
GROUP BY USER_NAME, day
ORDER BY failed_attempts DESC;
