-- ============================================================
-- Query 05: Alcohol Impact Deep Dive
-- ============================================================
-- Business question:
--   How does drinking alcohol affect same-night sleep quality,
--   next-morning recovery, HRV, and resting heart rate?
--   Is the effect consistent or does it vary?
--
-- Approach:
--   Multi-layered CTE chain:
--     1. Identify alcohol vs non-alcohol nights from journal_pivot.
--     2. Join same-night primary sleep metrics.
--     3. Use LEAD to get next-day recovery/HRV/RHR.
--     4. Compare all metrics between the two cohorts.
--     5. Include running averages for trend context.
--
-- Techniques: Multi-CTE, LEAD, FILTER, window running averages.
-- ============================================================

WITH alcohol_days AS (
    -- Flag each day as alcohol or not
    SELECT
        dc.cycle_date,
        dc.recovery_score,
        dc.hrv,
        dc.resting_hr,
        dc.day_strain,
        COALESCE(jp.have_any_alcoholic_drinks, FALSE) AS had_alcohol
    FROM daily_cycles dc
    LEFT JOIN journal_pivot jp ON dc.cycle_date = jp.cycle_date
),

with_sleep AS (
    -- Attach same-night primary sleep metrics
    SELECT
        ad.*,
        ss.sleep_efficiency,
        ss.deep_sleep_min,
        ss.rem_sleep_min,
        ss.asleep_duration_min,
        ss.sleep_debt_min,
        ROUND(ss.deep_sleep_min * 100.0
              / NULLIF(ss.asleep_duration_min, 0), 1) AS deep_pct,
        ROUND(ss.rem_sleep_min * 100.0
              / NULLIF(ss.asleep_duration_min, 0), 1) AS rem_pct
    FROM alcohol_days ad
    LEFT JOIN sleep_sessions ss
        ON ss.cycle_date = ad.cycle_date AND ss.is_nap = FALSE
),

with_next_day AS (
    -- Pair with next-day physiology
    SELECT
        *,
        LEAD(recovery_score) OVER (ORDER BY cycle_date) AS next_recovery,
        LEAD(hrv)            OVER (ORDER BY cycle_date) AS next_hrv,
        LEAD(resting_hr)     OVER (ORDER BY cycle_date) AS next_rhr
    FROM with_sleep
)

-- ---- Aggregate comparison: alcohol nights vs sober nights ----
SELECT
    CASE WHEN had_alcohol THEN 'Alcohol' ELSE 'No Alcohol' END AS cohort,
    COUNT(*)                                                    AS nights,

    -- Same-night sleep
    ROUND(AVG(sleep_efficiency), 1)     AS avg_sleep_efficiency,
    ROUND(AVG(deep_pct), 1)             AS avg_deep_pct,
    ROUND(AVG(rem_pct), 1)              AS avg_rem_pct,
    ROUND(AVG(asleep_duration_min), 0)  AS avg_asleep_min,
    ROUND(AVG(sleep_debt_min), 0)       AS avg_sleep_debt,

    -- Next-day physiology
    ROUND(AVG(next_recovery), 1)        AS avg_next_recovery,
    ROUND(AVG(next_hrv), 1)             AS avg_next_hrv,
    ROUND(AVG(next_rhr), 1)             AS avg_next_rhr,

    -- Variability
    ROUND(STDDEV(next_recovery), 1)     AS stddev_next_recovery,
    ROUND(STDDEV(sleep_efficiency), 1)  AS stddev_sleep_efficiency

FROM with_next_day
WHERE recovery_score IS NOT NULL
GROUP BY had_alcohol
ORDER BY cohort;
