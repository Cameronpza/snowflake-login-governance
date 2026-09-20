-- Detection 2 (PRD "Weak auth usage"): shipped as a standing compliance tile,
-- not an anomaly flag -- MFA adoption is 0% account-wide, so there's no
-- baseline to deviate from (see PRD "Detection 2" for the full reasoning).
-- Three statements: overall MFA rate, per-user MFA rate, and programmatic
-- access token usage (a separate risk category -- long-lived token exposure
-- vs. credential guessing -- surfaced as its own tile rather than lumped in).
--
-- Params: excluded_users - list of USER_NAME values to exclude.

-- Statement 1: overall compliance rate (the tile's headline number).
SELECT
    COUNT(*) AS total_logins,
    COUNT_IF(SECOND_AUTHENTICATION_FACTOR IS NOT NULL) AS mfa_logins,
    ROUND(100.0 * COUNT_IF(SECOND_AUTHENTICATION_FACTOR IS NOT NULL) / COUNT(*), 1) AS mfa_pct
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE USER_NAME NOT IN (%(excluded_users)s);

-- Statement 2: per-user breakdown.
SELECT
    USER_NAME,
    COUNT(*) AS total_logins,
    COUNT_IF(SECOND_AUTHENTICATION_FACTOR IS NOT NULL) AS mfa_logins,
    ROUND(100.0 * COUNT_IF(SECOND_AUTHENTICATION_FACTOR IS NOT NULL) / COUNT(*), 1) AS mfa_pct
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE USER_NAME NOT IN (%(excluded_users)s)
GROUP BY USER_NAME
ORDER BY total_logins DESC;

-- Statement 3: programmatic access token usage, per user.
SELECT
    USER_NAME,
    COUNT(*) AS pat_logins
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE FIRST_AUTHENTICATION_FACTOR = 'PROGRAMMATIC_ACCESS_TOKEN'
  AND USER_NAME NOT IN (%(excluded_users)s)
GROUP BY USER_NAME
ORDER BY pat_logins DESC;
