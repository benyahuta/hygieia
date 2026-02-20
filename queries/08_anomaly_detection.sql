-- ============================================================
-- Query 08: Statistical Anomaly Detection
-- ============================================================
-- Business question:
--   On which days did any key biometric (HRV, RHR, recovery,
--   sleep efficiency) fall outside 2 standard deviations from
--   the user's 30-day rolling baseline? These outliers may signal
--   illness, over-training, lifestyle changes, or measurement issues.
--
-- Approach:
--   Compute 30-day rolling mean and stddev for each metric.
--   Flag any day where the observed value is >2 stddev away.
--   Return only flagged days, with context about which metric(s)
--   triggered and how far they deviated (z-score).
--
-- Techniques: Window functions (AVG, STDDEV OVER ROWS BETWEEN),
--   CASE flags, lateral z-score calculation, FILTER.
-- ============================================================

WITH baselines AS (
    SELECT
        dc.cycle_date,
        dc.recovery_score,
        dc.hrv,
        dc.resting_hr,
        ss.sleep_efficiency,

        -- 30-day rolling stats for recovery
        AVG(dc.recovery_score)    OVER w30 AS recovery_avg_30d,
        STDDEV(dc.recovery_score) OVER w30 AS recovery_std_30d,

        -- 30-day rolling stats for HRV
        AVG(dc.hrv)    OVER w30 AS hrv_avg_30d,
        STDDEV(dc.hrv) OVER w30 AS hrv_std_30d,

        -- 30-day rolling stats for RHR
        AVG(dc.resting_hr)    OVER w30 AS rhr_avg_30d,
        STDDEV(dc.resting_hr) OVER w30 AS rhr_std_30d,

        -- 30-day rolling stats for sleep efficiency
        AVG(ss.sleep_efficiency)    OVER w30 AS eff_avg_30d,
        STDDEV(ss.sleep_efficiency) OVER w30 AS eff_std_30d

    FROM daily_cycles dc
    LEFT JOIN sleep_sessions ss
        ON ss.cycle_date = dc.cycle_date AND ss.is_nap = FALSE
    WINDOW w30 AS (ORDER BY dc.cycle_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
),

flagged AS (
    SELECT
        cycle_date,
        recovery_score,
        hrv,
        resting_hr,
        sleep_efficiency,

        -- Z-scores (how many stddev from rolling mean)
        ROUND((recovery_score - recovery_avg_30d)
              / NULLIF(recovery_std_30d, 0), 2)       AS recovery_z,
        ROUND((hrv - hrv_avg_30d)
              / NULLIF(hrv_std_30d, 0), 2)             AS hrv_z,
        ROUND((resting_hr - rhr_avg_30d)
              / NULLIF(rhr_std_30d, 0), 2)             AS rhr_z,
        ROUND((sleep_efficiency - eff_avg_30d)
              / NULLIF(eff_std_30d, 0), 2)             AS efficiency_z,

        -- Boolean flags
        ABS(recovery_score - recovery_avg_30d) > 2 * NULLIF(recovery_std_30d, 0)   AS recovery_anomaly,
        ABS(hrv - hrv_avg_30d)                 > 2 * NULLIF(hrv_std_30d, 0)         AS hrv_anomaly,
        ABS(resting_hr - rhr_avg_30d)          > 2 * NULLIF(rhr_std_30d, 0)         AS rhr_anomaly,
        ABS(sleep_efficiency - eff_avg_30d)    > 2 * NULLIF(eff_std_30d, 0)         AS efficiency_anomaly,

        -- Rolling baselines for context
        ROUND(recovery_avg_30d, 1) AS recovery_baseline,
        ROUND(hrv_avg_30d, 1)      AS hrv_baseline,
        ROUND(rhr_avg_30d, 1)      AS rhr_baseline,
        ROUND(eff_avg_30d, 1)      AS eff_baseline

    FROM baselines
)

SELECT
    cycle_date,
    recovery_score,    recovery_baseline,    recovery_z,    recovery_anomaly,
    hrv,               hrv_baseline,         hrv_z,         hrv_anomaly,
    resting_hr,        rhr_baseline,         rhr_z,         rhr_anomaly,
    sleep_efficiency,  eff_baseline,         efficiency_z,  efficiency_anomaly
FROM flagged
WHERE recovery_anomaly = TRUE
   OR hrv_anomaly = TRUE
   OR rhr_anomaly = TRUE
   OR efficiency_anomaly = TRUE
ORDER BY cycle_date;
