-- ============================================================
-- Query 11: Sleep Architecture Analysis
-- ============================================================
-- Business question:
--   How does the composition of sleep (not just duration) affect
--   next-day recovery? Is deep sleep or REM more predictive?
--   What's the ideal sleep architecture for peak performance?
--
-- Approach:
--   Compute sleep stage percentages, bucket them into quality tiers,
--   and correlate with next-day recovery. Also track how sleep
--   architecture shifts over time (are you getting more/less deep sleep?).
--
-- Techniques: Window functions, NTILE, LEAD, correlation via
--   conditional aggregation, percentile bucketing.
-- ============================================================

WITH sleep_arch AS (
    SELECT
        ss.cycle_date,
        ss.asleep_duration_min,
        ss.deep_sleep_min,
        ss.rem_sleep_min,
        ss.light_sleep_min,
        ss.sleep_efficiency,
        ROUND(ss.deep_sleep_min * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS deep_pct,
        ROUND(ss.rem_sleep_min  * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS rem_pct,
        ROUND(ss.light_sleep_min * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS light_pct,
        -- Next-day recovery
        LEAD(dc.recovery_score) OVER (ORDER BY ss.cycle_date) AS next_recovery,
        LEAD(dc.hrv)            OVER (ORDER BY ss.cycle_date) AS next_hrv
    FROM sleep_sessions ss
    JOIN daily_cycles dc ON dc.cycle_date = ss.cycle_date
    WHERE ss.is_nap = FALSE
      AND ss.asleep_duration_min > 0
),

with_tiers AS (
    SELECT
        *,
        NTILE(3) OVER (ORDER BY deep_pct) AS deep_tier,
        NTILE(3) OVER (ORDER BY rem_pct)  AS rem_tier,
        NTILE(3) OVER (ORDER BY asleep_duration_min) AS duration_tier
    FROM sleep_arch
    WHERE next_recovery IS NOT NULL
)

-- How does each sleep component predict next-day recovery?
SELECT
    'Deep Sleep' AS sleep_component,
    CASE deep_tier
        WHEN 1 THEN 'Low'
        WHEN 2 THEN 'Medium'
        WHEN 3 THEN 'High'
    END AS tier,
    COUNT(*) AS nights,
    ROUND(AVG(deep_pct), 1) AS avg_pct,
    ROUND(AVG(next_recovery), 1) AS avg_next_recovery,
    ROUND(AVG(next_hrv), 1) AS avg_next_hrv,
    ROUND(STDDEV(next_recovery), 1) AS stddev_recovery
FROM with_tiers
GROUP BY deep_tier
UNION ALL
SELECT
    'REM Sleep',
    CASE rem_tier WHEN 1 THEN 'Low' WHEN 2 THEN 'Medium' WHEN 3 THEN 'High' END,
    COUNT(*),
    ROUND(AVG(rem_pct), 1),
    ROUND(AVG(next_recovery), 1),
    ROUND(AVG(next_hrv), 1),
    ROUND(STDDEV(next_recovery), 1)
FROM with_tiers
GROUP BY rem_tier
UNION ALL
SELECT
    'Total Duration',
    CASE duration_tier WHEN 1 THEN 'Short' WHEN 2 THEN 'Medium' WHEN 3 THEN 'Long' END,
    COUNT(*),
    ROUND(AVG(asleep_duration_min / 60.0), 1),
    ROUND(AVG(next_recovery), 1),
    ROUND(AVG(next_hrv), 1),
    ROUND(STDDEV(next_recovery), 1)
FROM with_tiers
GROUP BY duration_tier
ORDER BY sleep_component, tier;
