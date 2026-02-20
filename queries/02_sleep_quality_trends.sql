-- ============================================================
-- Query 02: Rolling Sleep Quality Trends
-- ============================================================
-- Business question:
--   How has sleep quality evolved over time, and which nights
--   were statistical anomalies compared to recent personal trends?
--
-- Approach:
--   Compute 7-day and 30-day rolling averages of sleep efficiency,
--   deep-sleep %, REM %, and sleep debt for primary sleeps (not naps).
--   Flag nights where sleep efficiency deviates more than 1 standard
--   deviation from the 7-day rolling average.
--
-- Techniques: Window functions (AVG / STDDEV OVER ROWS BETWEEN),
--   derived columns, CASE anomaly flag.
-- ============================================================

WITH nightly AS (
    -- One row per primary sleep (exclude naps)
    SELECT
        ss.cycle_date,
        ss.sleep_efficiency,
        ss.deep_sleep_min,
        ss.rem_sleep_min,
        ss.asleep_duration_min,
        ss.sleep_debt_min,
        -- Percentage of total sleep that was deep / REM
        ROUND(ss.deep_sleep_min * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS deep_pct,
        ROUND(ss.rem_sleep_min  * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS rem_pct
    FROM sleep_sessions ss
    WHERE ss.is_nap = FALSE
),

rolling AS (
    SELECT
        cycle_date,
        sleep_efficiency,
        deep_pct,
        rem_pct,
        sleep_debt_min,
        asleep_duration_min,

        -- 7-day rolling averages
        ROUND(AVG(sleep_efficiency)    OVER w7, 1)  AS eff_7d_avg,
        ROUND(AVG(deep_pct)            OVER w7, 1)  AS deep_pct_7d_avg,
        ROUND(AVG(rem_pct)             OVER w7, 1)  AS rem_pct_7d_avg,
        ROUND(AVG(sleep_debt_min)      OVER w7, 1)  AS debt_7d_avg,

        -- 30-day rolling averages
        ROUND(AVG(sleep_efficiency)    OVER w30, 1) AS eff_30d_avg,
        ROUND(AVG(deep_pct)            OVER w30, 1) AS deep_pct_30d_avg,
        ROUND(AVG(rem_pct)             OVER w30, 1) AS rem_pct_30d_avg,
        ROUND(AVG(sleep_debt_min)      OVER w30, 1) AS debt_30d_avg,

        -- 7-day rolling stddev for anomaly detection
        STDDEV(sleep_efficiency) OVER w7 AS eff_7d_stddev

    FROM nightly
    WINDOW
        w7  AS (ORDER BY cycle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
        w30 AS (ORDER BY cycle_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
)

SELECT
    cycle_date,
    sleep_efficiency,
    eff_7d_avg,
    eff_30d_avg,
    deep_pct,
    deep_pct_7d_avg,
    rem_pct,
    rem_pct_7d_avg,
    ROUND(sleep_debt_min, 0)  AS sleep_debt_min,
    ROUND(debt_7d_avg, 0)     AS debt_7d_avg,
    ROUND(asleep_duration_min / 60.0, 1) AS hours_slept,

    -- Anomaly flag: efficiency deviates > 1 stddev from 7-day rolling mean
    CASE
        WHEN eff_7d_stddev > 0
             AND ABS(sleep_efficiency - eff_7d_avg) > eff_7d_stddev
        THEN TRUE
        ELSE FALSE
    END AS is_anomaly

FROM rolling
ORDER BY cycle_date;
