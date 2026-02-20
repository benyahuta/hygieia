-- ============================================================
-- Query 04: Workout Performance by Recovery State
-- ============================================================
-- Business question:
--   Are workouts more productive (higher strain, more calories,
--   longer duration) when starting from a high-recovery state?
--   Should you train differently on red/yellow/green days?
--
-- Approach:
--   Bucket each day's recovery score into Whoop-style tiers:
--     Green  (>67%), Yellow (34–67%), Red (<34%).
--   Join workouts onto daily_cycles and compare workout metrics
--   across tiers. Also break down by activity type.
--
-- Techniques: CTE, CASE bucketing, JOIN, GROUP BY with ROLLUP.
-- ============================================================

WITH recovery_tiers AS (
    SELECT
        dc.cycle_date,
        dc.recovery_score,
        CASE
            WHEN dc.recovery_score > 67 THEN 'Green (>67%)'
            WHEN dc.recovery_score >= 34 THEN 'Yellow (34-67%)'
            ELSE 'Red (<34%)'
        END AS recovery_tier
    FROM daily_cycles dc
    WHERE dc.recovery_score IS NOT NULL
)

-- Workout metrics per recovery tier
SELECT
    rt.recovery_tier,
    w.activity_name,
    COUNT(*)                                  AS workout_count,
    ROUND(AVG(w.activity_strain), 1)          AS avg_strain,
    ROUND(AVG(w.energy_burned), 0)            AS avg_calories,
    ROUND(AVG(w.duration_min), 0)             AS avg_duration_min,
    ROUND(AVG(w.max_hr), 0)                   AS avg_max_hr,
    ROUND(AVG(w.avg_hr), 0)                   AS avg_avg_hr,
    -- Heart rate zone distribution
    ROUND(AVG(w.hr_zone1_pct + w.hr_zone2_pct), 1)  AS avg_low_zone_pct,
    ROUND(AVG(w.hr_zone4_pct + w.hr_zone5_pct), 1)  AS avg_high_zone_pct,
    ROUND(AVG(rt.recovery_score), 1)          AS avg_recovery_in_tier
FROM recovery_tiers rt
JOIN workouts w ON w.cycle_date = rt.cycle_date
GROUP BY ROLLUP (rt.recovery_tier, w.activity_name)
ORDER BY rt.recovery_tier NULLS LAST, w.activity_name NULLS LAST;
