-- ============================================================
-- Query 06: Finding Optimal Performance Conditions
-- ============================================================
-- Business question:
--   What combination of behaviors, sleep quality, and strain
--   produces the highest recovery scores? Which levers matter
--   most when they overlap?
--
-- Approach:
--   Bucket key controllable factors into binary high/low flags,
--   then use GROUPING SETS to analyze recovery across every
--   combination of those factors — from single-factor to
--   multi-factor interactions.
--
-- Techniques: GROUPING SETS, CASE bucketing, multi-table JOIN,
--   GROUPING() function for labelling.
-- ============================================================

WITH base AS (
    SELECT
        dc.cycle_date,
        dc.recovery_score,
        dc.hrv,
        dc.resting_hr,

        -- Sleep quality flag (efficiency above personal median)
        CASE WHEN ss.sleep_efficiency >= 90 THEN 'Good Sleep'
             ELSE 'Poor Sleep'
        END AS sleep_bucket,

        -- Strain level from the prior day (light vs heavy training)
        CASE WHEN dc.day_strain >= 14 THEN 'High Strain'
             ELSE 'Low Strain'
        END AS strain_bucket,

        -- Alcohol
        CASE WHEN COALESCE(jp.have_any_alcoholic_drinks, FALSE) THEN 'Alcohol' ELSE 'No Alcohol' END AS alcohol_flag,

        -- Caffeine
        CASE WHEN COALESCE(jp.consumed_caffeine, FALSE) THEN 'Caffeine' ELSE 'No Caffeine' END AS caffeine_flag

    FROM daily_cycles dc
    LEFT JOIN sleep_sessions ss
        ON ss.cycle_date = dc.cycle_date AND ss.is_nap = FALSE
    LEFT JOIN journal_pivot jp
        ON jp.cycle_date = dc.cycle_date
    WHERE dc.recovery_score IS NOT NULL
)

SELECT
    -- Use GROUPING() to label rolled-up dimensions as "ALL"
    CASE WHEN GROUPING(sleep_bucket)  = 1 THEN 'ALL' ELSE sleep_bucket  END AS sleep_quality,
    CASE WHEN GROUPING(strain_bucket) = 1 THEN 'ALL' ELSE strain_bucket END AS strain_level,
    CASE WHEN GROUPING(alcohol_flag)  = 1 THEN 'ALL' ELSE alcohol_flag  END AS alcohol,
    CASE WHEN GROUPING(caffeine_flag) = 1 THEN 'ALL' ELSE caffeine_flag END AS caffeine,

    COUNT(*)                            AS days,
    ROUND(AVG(recovery_score), 1)       AS avg_recovery,
    ROUND(AVG(hrv), 1)                  AS avg_hrv,
    ROUND(AVG(resting_hr), 1)           AS avg_rhr,
    ROUND(STDDEV(recovery_score), 1)    AS stddev_recovery

FROM base
GROUP BY GROUPING SETS (
    (),                                           -- grand total
    (sleep_bucket),                               -- single factors
    (strain_bucket),
    (alcohol_flag),
    (caffeine_flag),
    (sleep_bucket, alcohol_flag),                  -- two-factor combos
    (sleep_bucket, strain_bucket),
    (alcohol_flag, caffeine_flag),
    (sleep_bucket, alcohol_flag, strain_bucket),   -- three-factor
    (sleep_bucket, alcohol_flag, strain_bucket, caffeine_flag)  -- full
)
HAVING COUNT(*) >= 2   -- require at least 2 data points
ORDER BY avg_recovery DESC;
