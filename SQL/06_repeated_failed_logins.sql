-- Detection 1 (PRD "Repeated failed logins"): flags a failed login when
-- either of these hold:
--   (a) the same USER_NAME racked up >= :threshold failed logins within a
--       trailing :window_minutes sliding window (burst detection), or
--   (b) Snowflake itself already escalated the event -- ERROR_MESSAGE
--       'OVERFLOW_FAILURE_EVENTS_ELIDED' (it collapsed a larger burst than
--       what's recorded) or 'USER_LOCKED_TEMP' (account already locked) --
--       regardless of the raw count, since these are stronger signals than
--       the threshold heuristic.
--
-- Params (bind as a dict via snowflake-connector-python, pyformat style):
--   excluded_users   - list of USER_NAME values to exclude (test/service accounts)
--   window_minutes   - sliding window size in minutes (PRD baseline: 10)
--   threshold        - failures within the window required to flag (PRD baseline: 5)

WITH failed AS (
    SELECT
        EVENT_TIMESTAMP,
        USER_NAME,
        CLIENT_IP,
        ERROR_CODE,
        ERROR_MESSAGE
    FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
    WHERE IS_SUCCESS = 'NO'
      AND USER_NAME NOT IN (%(excluded_users)s)
),
scored AS (
    SELECT
        f.EVENT_TIMESTAMP,
        f.USER_NAME,
        f.CLIENT_IP,
        f.ERROR_CODE,
        f.ERROR_MESSAGE,
        (
            SELECT COUNT(*)
            FROM failed f2
            WHERE f2.USER_NAME = f.USER_NAME
              AND f2.EVENT_TIMESTAMP
                  BETWEEN DATEADD('minute', -%(window_minutes)s, f.EVENT_TIMESTAMP)
                  AND f.EVENT_TIMESTAMP
        ) AS failures_in_window,
        f.ERROR_MESSAGE = 'OVERFLOW_FAILURE_EVENTS_ELIDED' AS is_overflow_elided,
        f.ERROR_MESSAGE = 'USER_LOCKED_TEMP' AS is_locked_temp
    FROM failed f
)
SELECT *
FROM scored
WHERE failures_in_window >= %(threshold)s
   OR is_overflow_elided
   OR is_locked_temp
ORDER BY EVENT_TIMESTAMP DESC;
