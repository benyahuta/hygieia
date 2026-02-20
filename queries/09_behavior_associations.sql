-- ============================================================
-- Query 09: Journal Behavior Co-occurrence & Associations
-- ============================================================
-- Business question:
--   Which behaviors tend to appear together? For any target
--   outcome (e.g. "Experienced acne?"), which other behaviors
--   are disproportionately common on those days?
--
-- This answers questions like:
--   "On days I had acne, what else was I doing differently?"
--   "When I drink alcohol, what other behaviors co-occur?"
--
-- Approach:
--   Self-join journal_entries to pair every behavior with every
--   other behavior on the same day. Compute:
--     - Co-occurrence rate (how often B is "yes" when A is "yes")
--     - Baseline rate (how often B is "yes" overall)
--     - Lift (co-occurrence / baseline) — >1 means positive assoc.
--   This is essentially market-basket analysis for health behaviors.
--
-- Techniques: Self-join, conditional aggregation, FILTER,
--   co-occurrence lift calculation, CTE.
-- ============================================================

WITH behavior_pairs AS (
    -- For every day, pair each behavior with every other behavior
    SELECT
        a.cycle_date,
        a.question AS behavior_a,
        a.answered_yes AS a_yes,
        b.question AS behavior_b,
        b.answered_yes AS b_yes
    FROM journal_entries a
    JOIN journal_entries b
        ON a.cycle_date = b.cycle_date
       AND a.question <> b.question
),

-- Baseline: how often each behavior is "yes" across all tracked days
baselines AS (
    SELECT
        question,
        COUNT(*) FILTER (WHERE answered_yes = TRUE)::NUMERIC / COUNT(*) AS baseline_rate,
        COUNT(*) FILTER (WHERE answered_yes = TRUE) AS yes_days,
        COUNT(*) AS total_days
    FROM journal_entries
    GROUP BY question
),

-- Co-occurrence: when behavior_a is "yes", how often is behavior_b also "yes"?
cooccurrence AS (
    SELECT
        behavior_a,
        behavior_b,
        COUNT(*) FILTER (WHERE a_yes = TRUE) AS a_yes_days,
        COUNT(*) FILTER (WHERE a_yes = TRUE AND b_yes = TRUE) AS both_yes_days,
        CASE
            WHEN COUNT(*) FILTER (WHERE a_yes = TRUE) > 0
            THEN COUNT(*) FILTER (WHERE a_yes = TRUE AND b_yes = TRUE)::NUMERIC
                 / COUNT(*) FILTER (WHERE a_yes = TRUE)
            ELSE 0
        END AS cooccurrence_rate
    FROM behavior_pairs
    GROUP BY behavior_a, behavior_b
)

SELECT
    c.behavior_a AS target_behavior,
    c.behavior_b AS associated_behavior,
    c.a_yes_days AS target_yes_days,
    c.both_yes_days,
    ROUND(c.cooccurrence_rate * 100, 1) AS cooccurrence_pct,
    ROUND(b.baseline_rate * 100, 1) AS baseline_pct,
    ROUND(
        CASE WHEN b.baseline_rate > 0
             THEN c.cooccurrence_rate / b.baseline_rate
             ELSE NULL
        END, 2
    ) AS lift
FROM cooccurrence c
JOIN baselines b ON b.question = c.behavior_b
WHERE c.a_yes_days >= 1
  AND c.both_yes_days >= 0
ORDER BY c.behavior_a, lift DESC NULLS LAST;
