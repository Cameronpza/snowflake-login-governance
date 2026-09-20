-- Detection 3 (PRD "Odd-hour logins"): flags logins outside a static,
-- account-wide business-hours window. Deliberately NOT a per-user learned
-- baseline -- data volume/skew here doesn't support one (see PRD
-- "Detection 3"). This is a coarse heuristic and should be labeled as such
-- in the dashboard, not presented as personalized anomaly detection.
--
-- Params:
--   excluded_users      - list of USER_NAME values to exclude
--   timezone             - Snowflake-recognized timezone name the business-hours
--                          window is defined in (e.g. 'UTC', 'America/New_York')
--   business_start_hour  - local hour (0-23) the window opens (PRD baseline: 8)
--   business_end_hour    - local hour (0-23) the window closes (PRD baseline: 18)

WITH local AS (
    SELECT
        EVENT_TIMESTAMP,
        CONVERT_TIMEZONE(%(timezone)s, EVENT_TIMESTAMP) AS local_event_timestamp,
        HOUR(CONVERT_TIMEZONE(%(timezone)s, EVENT_TIMESTAMP)) AS local_hour,
        USER_NAME,
        CLIENT_IP,
        IS_SUCCESS,
        FIRST_AUTHENTICATION_FACTOR
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
    WHERE USER_NAME NOT IN (%(excluded_users)s)
)
SELECT *
FROM local
WHERE local_hour < %(business_start_hour)s
   OR local_hour >= %(business_end_hour)s
ORDER BY EVENT_TIMESTAMP DESC;
