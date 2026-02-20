-- ============================================================
-- Query 03: Strain vs Next-Day Recovery Correlation
-- ============================================================
-- Business question:
--   Does pushing harder (higher day strain) help or hurt the
--   next morning's recovery score? At what strain level does
--   the relationship flip?
--
-- Approach:
--   Use LEAD() to pair each day's strain with the next day's
--   recovery. Bucket strain into quartiles with NTILE(4) and
--   compute average next-day recovery per quartile. Also show
--   the raw day-to-day pairs for scatter plotting.
--
-- Techniques: LEAD window function, NTILE, CTE, conditional agg.
-- ============================================================

WITH paired AS (
    -- Pair today's metrics with tomorrow's recovery
    SELECT
        cycle_date,
        day_strain,
        recovery_score,
        hrv,
        resting_hr,
        LEAD(recovery_score) OVER (ORDER BY cycle_date) AS next_day_recovery,
        LEAD(hrv)            OVER (ORDER BY cycle_date) AS next_day_hrv,
        LEAD(resting_hr)     OVER (ORDER BY cycle_date) AS next_day_rhr
    FROM daily_cycles
    WHERE day_strain IS NOT NULL
),

with_quartiles AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY day_strain) AS strain_quartile
    FROM paired
    WHERE next_day_recovery IS NOT NULL
)

-- Summary by strain quartile
SELECT
    strain_quartile,
    COUNT(*)                                          AS days,
    ROUND(MIN(day_strain), 1)                         AS strain_min,
    ROUND(MAX(day_strain), 1)                         AS strain_max,
    ROUND(AVG(day_strain), 1)                         AS avg_strain,
    ROUND(AVG(next_day_recovery), 1)                  AS avg_next_recovery,
    ROUND(AVG(next_day_hrv), 1)                       AS avg_next_hrv,
    ROUND(AVG(next_day_rhr), 1)                       AS avg_next_rhr,
    ROUND(STDDEV(next_day_recovery), 1)               AS stddev_next_recovery
FROM with_quartiles
GROUP BY strain_quartile
ORDER BY strain_quartile;

-- Uncomment below for the raw scatter-plot data:
-- SELECT cycle_date, day_strain, next_day_recovery
-- FROM with_quartiles
-- ORDER BY cycle_date;
