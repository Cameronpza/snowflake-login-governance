-- Time-of-day distribution and IP diversity -- needed for "odd-hour logins" and
-- to judge whether IP-based anomaly detection (new/unusual source) is viable.

SELECT
    HOUR(EVENT_TIMESTAMP) AS hour_of_day_utc,
    COUNT(*) AS attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY hour_of_day_utc
ORDER BY hour_of_day_utc;

SELECT
    DAYNAME(EVENT_TIMESTAMP) AS day_of_week,
    COUNT(*) AS attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY day_of_week
ORDER BY attempts DESC;

SELECT
    CLIENT_IP,
    COUNT(DISTINCT USER_NAME) AS distinct_users_from_ip,
    COUNT(*) AS attempts
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY CLIENT_IP
ORDER BY attempts DESC;

SELECT
    USER_NAME,
    COUNT(DISTINCT CLIENT_IP) AS distinct_ips
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY USER_NAME
ORDER BY distinct_ips DESC;
