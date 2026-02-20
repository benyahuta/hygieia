-- ============================================================
-- Query 07: Automated Weekly Summary Report
-- ============================================================
-- Business question:
--   Generate a concise week-over-week report covering recovery,
--   strain, sleep, and workout activity — the kind of summary
--   an operations team might review every Monday.
--
-- Approach:
--   Truncate dates to ISO weeks, aggregate key metrics per week,
--   and compute week-over-week deltas using LAG. Workout counts
--   come from a separate CTE to avoid correlated-subquery issues.
--
-- Techniques: DATE_TRUNC, GROUP BY, LAG, multi-CTE.
-- ============================================================

WITH weekly_workouts AS (
    SELECT
        DATE_TRUNC('week', cycle_date)::DATE AS week_start,
        COUNT(*) AS workout_count
    FROM workouts
    GROUP BY DATE_TRUNC('week', cycle_date)
),

weekly AS (
    SELECT
        DATE_TRUNC('week', dc.cycle_date)::DATE   AS week_start,
        COUNT(DISTINCT dc.cycle_date)              AS days_tracked,

        -- Recovery
        ROUND(AVG(dc.recovery_score), 1)           AS avg_recovery,
        MIN(dc.recovery_score)                     AS min_recovery,
        MAX(dc.recovery_score)                     AS max_recovery,

        -- Strain
        ROUND(SUM(DISTINCT dc.day_strain), 1)      AS total_strain,
        ROUND(AVG(DISTINCT dc.day_strain), 1)      AS avg_daily_strain,

        -- HRV & RHR
        ROUND(AVG(dc.hrv), 1)                      AS avg_hrv,
        ROUND(AVG(dc.resting_hr), 1)               AS avg_rhr,

        -- Sleep (primary sleeps only)
        ROUND(AVG(ss.asleep_duration_min) / 60.0, 2) AS avg_hours_slept,
        ROUND(AVG(ss.sleep_efficiency), 1)            AS avg_sleep_efficiency

    FROM daily_cycles dc
    LEFT JOIN sleep_sessions ss
        ON ss.cycle_date = dc.cycle_date AND ss.is_nap = FALSE
    WHERE dc.recovery_score IS NOT NULL
    GROUP BY DATE_TRUNC('week', dc.cycle_date)
)

SELECT
    w.week_start,
    w.days_tracked,
    w.avg_recovery,
    w.min_recovery,
    w.max_recovery,

    -- Week-over-week recovery change
    ROUND(w.avg_recovery
        - LAG(w.avg_recovery) OVER (ORDER BY w.week_start), 1) AS recovery_wow_delta,

    w.total_strain,
    w.avg_daily_strain,
    w.avg_hrv,
    w.avg_rhr,
    w.avg_hours_slept,
    w.avg_sleep_efficiency,
    COALESCE(ww.workout_count, 0) AS workout_count

FROM weekly w
LEFT JOIN weekly_workouts ww ON ww.week_start = w.week_start
ORDER BY w.week_start;
