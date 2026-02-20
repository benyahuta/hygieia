-- ============================================================
-- Query 01: Behavioral Impact on Recovery
-- ============================================================
-- Business question:
--   Which daily journal behaviors (alcohol, supplements, caffeine,
--   etc.) are most strongly associated with higher or lower
--   recovery scores, HRV, and resting heart rate?
--
-- Approach:
--   For every boolean journal behavior, compare the average recovery,
--   HRV, and RHR on days the behavior was reported "yes" vs "no".
--   Include sample sizes and standard deviations so we can gauge
--   whether differences are meaningful or just noise.
--
-- Techniques: CTE, UNPIVOT via UNION ALL, conditional aggregation,
--   CASE expressions, ROUND, COUNT, STDDEV.
-- ============================================================

WITH behavior_flags AS (
    -- Join pivoted journal answers onto the daily cycle metrics.
    -- Each row = one day with its behaviors + physiology.
    SELECT
        dc.cycle_date,
        dc.recovery_score,
        dc.hrv,
        dc.resting_hr,
        jp.have_any_alcoholic_drinks,
        jp.took_ashwaganda,
        jp.took_adhd_medication,
        jp.experienced_acne,
        jp.consumed_caffeine,
        jp.avoided_processed_foods,
        jp.took_creatine,
        jp.consumed_dairy,
        jp.took_a_glp1,
        jp.took_a_magnesium_supplement,
        jp.took_a_zinc_supplement,
        jp.took_vitamin_c,
        jp.took_vitamin_d,
        jp.took_ltheanine_supplements,
        jp.ate_food_close_to_bedtime,
        jp.read_nonscreened_device_while_in_bed,
        jp.saw_artificial_light_upon_waking_up
    FROM daily_cycles dc
    JOIN journal_pivot jp ON dc.cycle_date = jp.cycle_date
    WHERE dc.recovery_score IS NOT NULL
),

-- Unpivot: turn each boolean column into (behavior_name, flag) rows
-- so we can aggregate generically across all behaviors.
unpivoted AS (
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Alcohol' AS behavior, have_any_alcoholic_drinks AS flag
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Ashwagandha', took_ashwaganda
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'ADHD Medication', took_adhd_medication
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Acne', experienced_acne
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Caffeine', consumed_caffeine
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Avoided Processed Foods', avoided_processed_foods
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Creatine', took_creatine
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Dairy', consumed_dairy
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'GLP-1', took_a_glp1
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Magnesium', took_a_magnesium_supplement
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Zinc', took_a_zinc_supplement
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Vitamin C', took_vitamin_c
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Vitamin D', took_vitamin_d
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'L-Theanine', took_ltheanine_supplements
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Food Close to Bedtime', ate_food_close_to_bedtime
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Read in Bed (non-screen)', read_nonscreened_device_while_in_bed
    FROM behavior_flags
    UNION ALL
    SELECT cycle_date, recovery_score, hrv, resting_hr,
           'Artificial Light on Waking', saw_artificial_light_upon_waking_up
    FROM behavior_flags
)

SELECT
    behavior,

    -- "Yes" cohort
    COUNT(*) FILTER (WHERE flag = TRUE)            AS yes_days,
    ROUND(AVG(recovery_score) FILTER (WHERE flag = TRUE), 1)  AS avg_recovery_yes,
    ROUND(AVG(hrv)            FILTER (WHERE flag = TRUE), 1)  AS avg_hrv_yes,
    ROUND(AVG(resting_hr)     FILTER (WHERE flag = TRUE), 1)  AS avg_rhr_yes,

    -- "No" cohort
    COUNT(*) FILTER (WHERE flag = FALSE)           AS no_days,
    ROUND(AVG(recovery_score) FILTER (WHERE flag = FALSE), 1) AS avg_recovery_no,
    ROUND(AVG(hrv)            FILTER (WHERE flag = FALSE), 1) AS avg_hrv_no,
    ROUND(AVG(resting_hr)     FILTER (WHERE flag = FALSE), 1) AS avg_rhr_no,

    -- Delta (yes minus no) — positive = behavior helps recovery
    ROUND(AVG(recovery_score) FILTER (WHERE flag = TRUE)
        - AVG(recovery_score) FILTER (WHERE flag = FALSE), 1) AS recovery_delta,

    -- Spread indicators for significance
    ROUND(STDDEV(recovery_score) FILTER (WHERE flag = TRUE), 1)  AS stddev_yes,
    ROUND(STDDEV(recovery_score) FILTER (WHERE flag = FALSE), 1) AS stddev_no

FROM unpivoted
WHERE flag IS NOT NULL
GROUP BY behavior
ORDER BY recovery_delta DESC NULLS LAST;
