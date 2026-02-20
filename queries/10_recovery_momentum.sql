-- ============================================================
-- Query 10: Recovery Momentum & Readiness Trends
-- ============================================================
-- Business question:
--   Is recovery trending up or down? How many consecutive
--   "green" or "red" days have there been? What's the body's
--   current trajectory — building fitness or accumulating fatigue?
--
-- This gives a "readiness forecast" by looking at:
--   - Consecutive green/yellow/red day streaks
--   - 7-day recovery momentum (slope direction)
--   - Strain-to-recovery balance (are you recovering what you spend?)
--   - HRV trend direction over the last 7 days
--
-- Techniques: Window functions, LAG, running sums, gap-and-island
--   for streak detection, CASE for trend classification.
-- ============================================================

WITH base AS (
    SELECT
        cycle_date,
        recovery_score,
        hrv,
        resting_hr,
        day_strain,
        CASE
            WHEN recovery_score > 67 THEN 'Green'
            WHEN recovery_score >= 34 THEN 'Yellow'
            ELSE 'Red'
        END AS recovery_zone,

        -- 7-day rolling averages
        AVG(recovery_score) OVER w7 AS recovery_7d_avg,
        AVG(hrv)            OVER w7 AS hrv_7d_avg,
        AVG(day_strain)     OVER w7 AS strain_7d_avg,

        -- Strain-to-recovery ratio
        CASE WHEN day_strain > 0
             THEN ROUND(recovery_score / day_strain, 1)
             ELSE NULL
        END AS recovery_per_strain

    FROM daily_cycles
    WHERE recovery_score IS NOT NULL
    WINDOW w7 AS (ORDER BY cycle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
),

-- Second CTE: now we can safely LAG over the rolling averages
daily AS (
    SELECT
        *,
        LAG(recovery_score) OVER (ORDER BY cycle_date) AS prev_recovery,
        LAG(recovery_7d_avg) OVER (ORDER BY cycle_date) AS prev_recovery_7d_avg,
        LAG(hrv_7d_avg)      OVER (ORDER BY cycle_date) AS prev_hrv_7d_avg
    FROM base
),

-- Gap-and-island: detect consecutive streaks of the same recovery zone
streaks AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY cycle_date)
        - ROW_NUMBER() OVER (PARTITION BY recovery_zone ORDER BY cycle_date) AS streak_group
    FROM daily
),

streak_lengths AS (
    SELECT
        *,
        COUNT(*) OVER (PARTITION BY recovery_zone, streak_group) AS streak_length
    FROM streaks
)

SELECT
    cycle_date,
    recovery_score,
    recovery_zone,
    hrv,
    resting_hr,
    day_strain,

    -- Current streak info
    streak_length AS consecutive_days_in_zone,

    -- 7-day rolling averages
    ROUND(recovery_7d_avg, 1) AS recovery_7d_avg,
    ROUND(hrv_7d_avg, 1)      AS hrv_7d_avg,
    ROUND(strain_7d_avg, 1)   AS strain_7d_avg,

    -- Trend direction
    CASE
        WHEN recovery_7d_avg > prev_recovery_7d_avg + 2 THEN 'Improving'
        WHEN recovery_7d_avg < prev_recovery_7d_avg - 2 THEN 'Declining'
        ELSE 'Stable'
    END AS recovery_trend,

    CASE
        WHEN hrv_7d_avg > prev_hrv_7d_avg + 1 THEN 'Improving'
        WHEN hrv_7d_avg < prev_hrv_7d_avg - 1 THEN 'Declining'
        ELSE 'Stable'
    END AS hrv_trend,

    -- Day-over-day change
    recovery_score - prev_recovery AS recovery_delta,
    recovery_per_strain

FROM streak_lengths
ORDER BY cycle_date;
