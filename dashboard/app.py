"""
Health Analytics Dashboard
===========================
Streamlit app that visualizes Whoop biometric data from PostgreSQL.
All data retrieval uses raw SQL — no pandas transformations on the data itself.

Usage:
    streamlit run dashboard/app.py
"""

import os
import pandas as pd
import psycopg2
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
DB_PARAMS = {
    "dbname": "health_analytics",
    "user": os.environ.get("PGUSER", os.environ.get("USER", "postgres")),
    "host": os.environ.get("PGHOST", "localhost"),
    "port": os.environ.get("PGPORT", "5432"),
}
pw = os.environ.get("PGPASSWORD", "")
if pw:
    DB_PARAMS["password"] = pw


@st.cache_data(ttl=300)
def run_query(sql, params=None):
    """Execute a SQL query and return results as a DataFrame."""
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


# Friendly names for journal questions
QUESTION_LABELS = {
    "Have any alcoholic drinks?": "Alcohol",
    "Took ashwaganda?": "Ashwagandha",
    "Took AD(H)D medication?": "ADHD Medication",
    "Experienced acne?": "Acne",
    "Consumed caffeine?": "Caffeine",
    "Avoided processed foods?": "Avoided Processed Foods",
    "Took creatine?": "Creatine",
    "Consumed dairy?": "Dairy",
    "Took a GLP-1?": "GLP-1",
    "Took a magnesium supplement?": "Magnesium",
    "Took a zinc supplement?": "Zinc",
    "Took vitamin C?": "Vitamin C",
    "Took vitamin D?": "Vitamin D",
    "Took L-theanine supplements?": "L-Theanine",
    "Ate food close to bedtime?": "Ate Before Bed",
    "Read (non-screened device) while in bed?": "Read in Bed",
    "Saw artificial light upon waking up?": "Morning Light Exposure",
}


def friendly_name(question):
    return QUESTION_LABELS.get(question, question.rstrip("?"))


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Health Analytics", page_icon="*", layout="wide")
st.title("Health Analytics Dashboard")
st.caption("Personal Whoop biometric data — powered by PostgreSQL & Streamlit")

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

date_range_df = run_query("SELECT MIN(cycle_date) AS mn, MAX(cycle_date) AS mx FROM daily_cycles")
min_date = pd.to_datetime(date_range_df["mn"].iloc[0]).date()
max_date = pd.to_datetime(date_range_df["mx"].iloc[0]).date()

date_from, date_to = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

behaviors_df = run_query("SELECT DISTINCT question FROM journal_entries ORDER BY question")
behavior_options = behaviors_df["question"].tolist()
selected_behavior = st.sidebar.selectbox(
    "Highlight journal behavior",
    options=["None"] + behavior_options,
    format_func=lambda x: friendly_name(x) if x != "None" else "None",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Navigation**")
st.sidebar.markdown("""
- [Today's Snapshot](#today-s-snapshot)
- [Recovery & HRV Trends](#recovery-hrv-over-time)
- [Recovery Momentum](#recovery-momentum)
- [Behavioral Impact](#how-behaviors-affect-recovery)
- [Behavior Associations](#behavior-associations)
- [Sleep Stages](#nightly-sleep-stages)
- [Sleep Architecture](#sleep-architecture-next-day-recovery)
- [Strain vs Recovery](#day-strain-vs-next-day-recovery)
- [Workout Performance](#workout-performance-by-recovery-state)
""")

# ===================================================================
# 1. TODAY'S SNAPSHOT — overview cards with deltas
# ===================================================================
st.header("Today's Snapshot")

latest = run_query("""
    SELECT
        cycle_date, recovery_score, hrv, resting_hr, day_strain,
        LAG(recovery_score) OVER (ORDER BY cycle_date) AS prev_recovery,
        LAG(hrv)            OVER (ORDER BY cycle_date) AS prev_hrv,
        LAG(resting_hr)     OVER (ORDER BY cycle_date) AS prev_rhr
    FROM daily_cycles
    WHERE recovery_score IS NOT NULL
    ORDER BY cycle_date DESC
    LIMIT 2
""")

latest_sleep = run_query("""
    SELECT sleep_efficiency, asleep_duration_min,
           LAG(sleep_efficiency) OVER (ORDER BY cycle_date) AS prev_eff
    FROM sleep_sessions
    WHERE is_nap = FALSE AND sleep_efficiency IS NOT NULL
    ORDER BY cycle_date DESC
    LIMIT 2
""")

# Recovery zone color
def recovery_zone_label(score):
    if score > 67:
        return "Green"
    elif score >= 34:
        return "Yellow"
    return "Red"

cols = st.columns(6)
if not latest.empty:
    r = latest.iloc[0]
    zone = recovery_zone_label(r["recovery_score"])
    recovery_delta = r["recovery_score"] - r["prev_recovery"] if pd.notna(r.get("prev_recovery")) else None
    hrv_delta = r["hrv"] - r["prev_hrv"] if pd.notna(r.get("prev_hrv")) else None
    rhr_delta = r["resting_hr"] - r["prev_rhr"] if pd.notna(r.get("prev_rhr")) else None

    cols[0].metric("Recovery", f"{r['recovery_score']:.0f}%",
                   delta=f"{recovery_delta:+.0f}%" if recovery_delta is not None else None)
    cols[1].metric("Zone", zone)
    cols[2].metric("HRV", f"{r['hrv']:.0f} ms",
                   delta=f"{hrv_delta:+.0f}" if hrv_delta is not None else None)
    cols[3].metric("Resting HR", f"{r['resting_hr']:.0f} bpm",
                   delta=f"{rhr_delta:+.0f}" if rhr_delta is not None else None,
                   delta_color="inverse")
    cols[4].metric("Day Strain", f"{r['day_strain']:.1f}" if pd.notna(r["day_strain"]) else "--")
if not latest_sleep.empty:
    s = latest_sleep.iloc[0]
    eff_delta = s["sleep_efficiency"] - s["prev_eff"] if pd.notna(s.get("prev_eff")) else None
    hours = s["asleep_duration_min"] / 60.0 if pd.notna(s["asleep_duration_min"]) else None
    cols[5].metric("Sleep",
                   f"{hours:.1f}h / {s['sleep_efficiency']:.0f}%" if hours else "--",
                   delta=f"{eff_delta:+.0f}% eff" if eff_delta is not None else None)

st.divider()

# ===================================================================
# 2. RECOVERY & HRV TIME SERIES with 7-day rolling average
# ===================================================================
st.header("Recovery & HRV Over Time")

ts_df = run_query("""
    SELECT
        cycle_date,
        recovery_score,
        hrv,
        AVG(recovery_score) OVER (ORDER BY cycle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS recovery_7d,
        AVG(hrv)            OVER (ORDER BY cycle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS hrv_7d
    FROM daily_cycles
    WHERE cycle_date BETWEEN %s AND %s
      AND recovery_score IS NOT NULL
    ORDER BY cycle_date
""", (date_from, date_to))

if not ts_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts_df["cycle_date"], y=ts_df["recovery_score"],
                             mode="markers+lines", name="Recovery %",
                             line=dict(color="#4CAF50", width=1), opacity=0.4))
    fig.add_trace(go.Scatter(x=ts_df["cycle_date"], y=ts_df["recovery_7d"],
                             mode="lines", name="Recovery 7-Day Avg",
                             line=dict(color="#4CAF50", width=3)))
    fig.add_trace(go.Scatter(x=ts_df["cycle_date"], y=ts_df["hrv"],
                             mode="markers+lines", name="HRV (ms)",
                             line=dict(color="#2196F3", width=1), opacity=0.4, yaxis="y2"))
    fig.add_trace(go.Scatter(x=ts_df["cycle_date"], y=ts_df["hrv_7d"],
                             mode="lines", name="HRV 7-Day Avg",
                             line=dict(color="#2196F3", width=3), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Recovery %", side="left"),
        yaxis2=dict(title="HRV (ms)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.15),
        height=420, margin=dict(t=10, b=60),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===================================================================
# 3. RECOVERY MOMENTUM — streak & trend info
# ===================================================================
st.header("Recovery Momentum")

momentum_df = run_query("""
    WITH base AS (
        SELECT
            cycle_date, recovery_score, hrv, day_strain,
            CASE WHEN recovery_score > 67 THEN 'Green'
                 WHEN recovery_score >= 34 THEN 'Yellow'
                 ELSE 'Red' END AS zone,
            AVG(recovery_score) OVER w7 AS rec_7d,
            AVG(hrv) OVER w7 AS hrv_7d
        FROM daily_cycles
        WHERE recovery_score IS NOT NULL
          AND cycle_date BETWEEN %s AND %s
        WINDOW w7 AS (ORDER BY cycle_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
    ),
    with_lag AS (
        SELECT *, LAG(rec_7d) OVER (ORDER BY cycle_date) AS prev_rec_7d
        FROM base
    ),
    streaks AS (
        SELECT *,
            ROW_NUMBER() OVER (ORDER BY cycle_date)
            - ROW_NUMBER() OVER (PARTITION BY zone ORDER BY cycle_date) AS grp
        FROM with_lag
    )
    SELECT cycle_date, recovery_score, zone, hrv, day_strain,
           ROUND(rec_7d, 1) AS recovery_7d_avg,
           ROUND(hrv_7d, 1) AS hrv_7d_avg,
           COUNT(*) OVER (PARTITION BY zone, grp) AS streak_days,
           CASE WHEN rec_7d > prev_rec_7d + 2 THEN 'Improving'
                WHEN rec_7d < prev_rec_7d - 2 THEN 'Declining'
                ELSE 'Stable' END AS trend
    FROM streaks
    ORDER BY cycle_date
""", (date_from, date_to))

if not momentum_df.empty:
    # Show latest momentum status
    last = momentum_df.iloc[-1]
    m_cols = st.columns(4)
    m_cols[0].metric("Current Zone", last["zone"], delta=f"{last['streak_days']} day streak")
    m_cols[1].metric("7-Day Avg Recovery", f"{last['recovery_7d_avg']}%")
    m_cols[2].metric("7-Day Avg HRV", f"{last['hrv_7d_avg']} ms")
    m_cols[3].metric("Trend", last["trend"])

    # Color-coded recovery timeline
    zone_colors = {"Green": "#4CAF50", "Yellow": "#FFC107", "Red": "#F44336"}
    fig_mom = go.Figure()
    for zone_name, color in zone_colors.items():
        mask = momentum_df[momentum_df["zone"] == zone_name]
        if not mask.empty:
            fig_mom.add_trace(go.Bar(
                x=mask["cycle_date"], y=mask["recovery_score"],
                name=zone_name, marker_color=color,
            ))
    fig_mom.update_layout(barmode="stack", height=280, margin=dict(t=10, b=40),
                          yaxis_title="Recovery %", showlegend=True,
                          legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_mom, use_container_width=True)

st.divider()

# ===================================================================
# 4. BEHAVIORAL IMPACT ON RECOVERY — clean table
# ===================================================================
st.header("How Behaviors Affect Recovery")
st.markdown("Compares average recovery on days you reported **Yes** vs **No** for each behavior. "
            "A positive delta means the behavior is associated with *higher* recovery.")

behavior_df = run_query("""
    WITH unpivoted AS (
        SELECT
            je.question AS behavior,
            je.answered_yes AS flag,
            dc.recovery_score,
            dc.hrv,
            dc.resting_hr
        FROM journal_entries je
        JOIN daily_cycles dc ON dc.cycle_date = je.cycle_date
        WHERE dc.recovery_score IS NOT NULL
          AND dc.cycle_date BETWEEN %s AND %s
    )
    SELECT
        behavior,
        COUNT(*) FILTER (WHERE flag = TRUE)                          AS yes_days,
        ROUND(AVG(recovery_score) FILTER (WHERE flag = TRUE), 1)     AS avg_recovery_yes,
        ROUND(AVG(hrv)            FILTER (WHERE flag = TRUE), 1)     AS avg_hrv_yes,
        ROUND(AVG(resting_hr)     FILTER (WHERE flag = TRUE), 1)     AS avg_rhr_yes,
        COUNT(*) FILTER (WHERE flag = FALSE)                         AS no_days,
        ROUND(AVG(recovery_score) FILTER (WHERE flag = FALSE), 1)    AS avg_recovery_no,
        ROUND(AVG(hrv)            FILTER (WHERE flag = FALSE), 1)    AS avg_hrv_no,
        ROUND(AVG(resting_hr)     FILTER (WHERE flag = FALSE), 1)    AS avg_rhr_no,
        ROUND(AVG(recovery_score) FILTER (WHERE flag = TRUE)
            - AVG(recovery_score) FILTER (WHERE flag = FALSE), 1)    AS recovery_delta
    FROM unpivoted
    WHERE flag IS NOT NULL
    GROUP BY behavior
    HAVING COUNT(*) FILTER (WHERE flag = TRUE) >= 1
       AND COUNT(*) FILTER (WHERE flag = FALSE) >= 1
    ORDER BY recovery_delta DESC NULLS LAST
""", (date_from, date_to))

if not behavior_df.empty:
    display_df = behavior_df.copy()
    display_df["behavior"] = display_df["behavior"].apply(friendly_name)
    display_df.columns = [
        "Behavior", "Yes Days", "Avg Recovery (Yes)", "Avg HRV (Yes)", "Avg RHR (Yes)",
        "No Days", "Avg Recovery (No)", "Avg HRV (No)", "Avg RHR (No)", "Recovery Impact"
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Bar chart of recovery impact
    fig_impact = px.bar(
        display_df, x="Recovery Impact", y="Behavior", orientation="h",
        color="Recovery Impact",
        color_continuous_scale=["#F44336", "#FFC107", "#4CAF50"],
        color_continuous_midpoint=0,
    )
    fig_impact.update_layout(height=max(300, len(display_df) * 30), margin=dict(t=10, b=20, l=10),
                             yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    st.plotly_chart(fig_impact, use_container_width=True)

st.divider()

# ===================================================================
# 5. BEHAVIOR ASSOCIATIONS — what co-occurs with what?
# ===================================================================
st.header("Behavior Associations")
st.markdown("When a target behavior is **Yes**, how much more (or less) likely are other behaviors? "
            "**Lift > 1** = positive association, **Lift < 1** = negative association.")

target_behavior = st.selectbox(
    "Select a target behavior to analyze",
    options=behavior_options,
    format_func=friendly_name,
    key="assoc_target",
)

assoc_df = run_query("""
    WITH behavior_pairs AS (
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
        WHERE a.cycle_date BETWEEN %s AND %s
    ),
    baselines AS (
        SELECT question,
               COUNT(*) FILTER (WHERE answered_yes) ::NUMERIC / COUNT(*) AS baseline_rate
        FROM journal_entries
        WHERE cycle_date BETWEEN %s AND %s
        GROUP BY question
    ),
    cooccurrence AS (
        SELECT behavior_a, behavior_b,
               COUNT(*) FILTER (WHERE a_yes) AS a_yes_days,
               COUNT(*) FILTER (WHERE a_yes AND b_yes) AS both_yes_days,
               CASE WHEN COUNT(*) FILTER (WHERE a_yes) > 0
                    THEN COUNT(*) FILTER (WHERE a_yes AND b_yes)::NUMERIC
                         / COUNT(*) FILTER (WHERE a_yes)
                    ELSE 0 END AS cooccurrence_rate
        FROM behavior_pairs
        GROUP BY behavior_a, behavior_b
    )
    SELECT
        c.behavior_b AS associated_behavior,
        c.a_yes_days AS target_yes_days,
        c.both_yes_days,
        ROUND(c.cooccurrence_rate * 100, 1) AS cooccurrence_pct,
        ROUND(b.baseline_rate * 100, 1) AS baseline_pct,
        ROUND(CASE WHEN b.baseline_rate > 0 THEN c.cooccurrence_rate / b.baseline_rate END, 2) AS lift
    FROM cooccurrence c
    JOIN baselines b ON b.question = c.behavior_b
    WHERE c.behavior_a = %s
      AND c.a_yes_days >= 1
    ORDER BY lift DESC NULLS LAST
""", (date_from, date_to, date_from, date_to, target_behavior))

if not assoc_df.empty:
    assoc_display = assoc_df.copy()
    assoc_display["associated_behavior"] = assoc_display["associated_behavior"].apply(friendly_name)
    assoc_display.columns = [
        "Associated Behavior", "Target Yes Days", "Both Yes Days",
        "Co-occurrence %", "Baseline %", "Lift"
    ]
    st.dataframe(assoc_display, use_container_width=True, hide_index=True)

    # Lift chart
    fig_lift = px.bar(
        assoc_display, x="Lift", y="Associated Behavior", orientation="h",
        color="Lift",
        color_continuous_scale=["#2196F3", "#e0e0e0", "#FF9800"],
        color_continuous_midpoint=1.0,
    )
    fig_lift.add_vline(x=1.0, line_dash="dash", line_color="gray")
    fig_lift.update_layout(height=max(300, len(assoc_display) * 28), margin=dict(t=10, b=20, l=10),
                           yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    st.plotly_chart(fig_lift, use_container_width=True)

st.divider()

# ===================================================================
# 6. SLEEP STAGE BREAKDOWN — stacked bar
# ===================================================================
st.header("Nightly Sleep Stages")

sleep_df = run_query("""
    SELECT
        cycle_date,
        ROUND(light_sleep_min / 60.0, 2) AS light_hours,
        ROUND(deep_sleep_min  / 60.0, 2) AS deep_hours,
        ROUND(rem_sleep_min   / 60.0, 2) AS rem_hours,
        ROUND(awake_duration_min / 60.0, 2) AS awake_hours
    FROM sleep_sessions
    WHERE is_nap = FALSE
      AND cycle_date BETWEEN %s AND %s
    ORDER BY cycle_date
""", (date_from, date_to))

if not sleep_df.empty:
    fig_sleep = go.Figure()
    for col, label, color in [
        ("deep_hours", "Deep Sleep", "#1a237e"),
        ("rem_hours", "REM Sleep", "#5c6bc0"),
        ("light_hours", "Light Sleep", "#9fa8da"),
        ("awake_hours", "Awake", "#e0e0e0"),
    ]:
        fig_sleep.add_trace(go.Bar(
            x=sleep_df["cycle_date"], y=sleep_df[col], name=label, marker_color=color,
        ))
    fig_sleep.update_layout(barmode="stack", height=350, margin=dict(t=10, b=40),
                            yaxis_title="Hours", legend=dict(orientation="h", y=-0.2),
                            hovermode="x unified")
    st.plotly_chart(fig_sleep, use_container_width=True)

st.divider()

# ===================================================================
# 7. SLEEP ARCHITECTURE — which sleep stages predict recovery?
# ===================================================================
st.header("Sleep Architecture & Next-Day Recovery")
st.markdown("Does more deep sleep or REM lead to better recovery the next day? "
            "Nights are bucketed into Low/Medium/High thirds for each component.")

arch_df = run_query("""
    WITH sleep_arch AS (
        SELECT
            ss.cycle_date,
            ss.asleep_duration_min,
            ROUND(ss.deep_sleep_min * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS deep_pct,
            ROUND(ss.rem_sleep_min  * 100.0 / NULLIF(ss.asleep_duration_min, 0), 1) AS rem_pct,
            LEAD(dc.recovery_score) OVER (ORDER BY ss.cycle_date) AS next_recovery
        FROM sleep_sessions ss
        JOIN daily_cycles dc ON dc.cycle_date = ss.cycle_date
        WHERE ss.is_nap = FALSE AND ss.asleep_duration_min > 0
    ),
    with_tiers AS (
        SELECT *,
            NTILE(3) OVER (ORDER BY deep_pct) AS deep_tier,
            NTILE(3) OVER (ORDER BY rem_pct)  AS rem_tier,
            NTILE(3) OVER (ORDER BY asleep_duration_min) AS dur_tier
        FROM sleep_arch WHERE next_recovery IS NOT NULL
    )
    SELECT 'Deep Sleep' AS component,
           CASE deep_tier WHEN 1 THEN 'Low' WHEN 2 THEN 'Medium' WHEN 3 THEN 'High' END AS tier,
           COUNT(*) AS nights, ROUND(AVG(deep_pct), 1) AS avg_value,
           ROUND(AVG(next_recovery), 1) AS avg_next_recovery
    FROM with_tiers GROUP BY deep_tier
    UNION ALL
    SELECT 'REM Sleep',
           CASE rem_tier WHEN 1 THEN 'Low' WHEN 2 THEN 'Medium' WHEN 3 THEN 'High' END,
           COUNT(*), ROUND(AVG(rem_pct), 1), ROUND(AVG(next_recovery), 1)
    FROM with_tiers GROUP BY rem_tier
    UNION ALL
    SELECT 'Total Duration',
           CASE dur_tier WHEN 1 THEN 'Short' WHEN 2 THEN 'Medium' WHEN 3 THEN 'Long' END,
           COUNT(*), ROUND(AVG(asleep_duration_min / 60.0), 1), ROUND(AVG(next_recovery), 1)
    FROM with_tiers GROUP BY dur_tier
    ORDER BY component, tier
""")

if not arch_df.empty:
    arch_df.columns = ["Sleep Component", "Tier", "Nights", "Avg Value", "Avg Next-Day Recovery"]
    fig_arch = px.bar(
        arch_df, x="Tier", y="Avg Next-Day Recovery", color="Sleep Component",
        barmode="group", text="Avg Next-Day Recovery",
        color_discrete_map={"Deep Sleep": "#1a237e", "REM Sleep": "#5c6bc0", "Total Duration": "#9fa8da"},
    )
    fig_arch.update_traces(textposition="outside")
    fig_arch.update_layout(height=380, margin=dict(t=10, b=40), yaxis_title="Avg Next-Day Recovery %")
    st.plotly_chart(fig_arch, use_container_width=True)

st.divider()

# ===================================================================
# 8. STRAIN VS NEXT-DAY RECOVERY — scatter with trendline
# ===================================================================
st.header("Day Strain vs Next-Day Recovery")

scatter_df = run_query("""
    SELECT
        cycle_date,
        day_strain,
        LEAD(recovery_score) OVER (ORDER BY cycle_date) AS next_recovery
    FROM daily_cycles
    WHERE day_strain IS NOT NULL
      AND cycle_date BETWEEN %s AND %s
    ORDER BY cycle_date
""", (date_from, date_to))

scatter_df = scatter_df.dropna(subset=["next_recovery"])

if not scatter_df.empty:
    fig_scatter = px.scatter(
        scatter_df, x="day_strain", y="next_recovery",
        labels={"day_strain": "Day Strain", "next_recovery": "Next-Day Recovery %"},
        hover_data=["cycle_date"],
        trendline="ols",
        color_discrete_sequence=["#4CAF50"],
    )
    fig_scatter.update_layout(height=400, margin=dict(t=10, b=40))
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# ===================================================================
# 9. WORKOUT PERFORMANCE BY RECOVERY STATE
# ===================================================================
st.header("Workout Performance by Recovery State")
st.markdown("Are workouts more productive when starting from a **green** recovery zone?")

workout_df = run_query("""
    SELECT
        CASE
            WHEN dc.recovery_score > 67 THEN 'Green (>67%%)'
            WHEN dc.recovery_score >= 34 THEN 'Yellow (34-67%%)'
            ELSE 'Red (<34%%)'
        END AS recovery_tier,
        COUNT(*) AS workouts,
        ROUND(AVG(w.activity_strain), 1) AS avg_strain,
        ROUND(AVG(w.energy_burned), 0)   AS avg_calories,
        ROUND(AVG(w.duration_min), 0)    AS avg_duration,
        ROUND(AVG(w.max_hr), 0)          AS avg_max_hr,
        ROUND(AVG(dc.recovery_score), 1) AS avg_recovery
    FROM workouts w
    JOIN daily_cycles dc ON dc.cycle_date = w.cycle_date
    WHERE dc.recovery_score IS NOT NULL
      AND dc.cycle_date BETWEEN %s AND %s
    GROUP BY 1
    ORDER BY avg_recovery DESC
""", (date_from, date_to))

if not workout_df.empty:
    workout_df.columns = ["Recovery Tier", "Workouts", "Avg Strain", "Avg Calories",
                          "Avg Duration (min)", "Avg Max HR", "Avg Recovery"]
    st.dataframe(workout_df, use_container_width=True, hide_index=True)

    fig_wo = px.bar(
        workout_df, x="Recovery Tier", y=["Avg Strain", "Avg Calories"],
        barmode="group", color_discrete_sequence=["#4CAF50", "#FF9800"],
    )
    fig_wo.update_layout(height=320, margin=dict(t=10, b=40), yaxis_title="Value")
    st.plotly_chart(fig_wo, use_container_width=True)

st.divider()

# ===================================================================
# 10. BEHAVIOR HIGHLIGHT — selected behavior over time
# ===================================================================
if selected_behavior != "None":
    label = friendly_name(selected_behavior)
    st.header(f"Recovery on {label} Days")

    beh_ts = run_query("""
        SELECT
            dc.cycle_date,
            dc.recovery_score,
            je.answered_yes
        FROM daily_cycles dc
        LEFT JOIN journal_entries je
            ON je.cycle_date = dc.cycle_date AND je.question = %s
        WHERE dc.recovery_score IS NOT NULL
          AND dc.cycle_date BETWEEN %s AND %s
        ORDER BY dc.cycle_date
    """, (selected_behavior, date_from, date_to))

    if not beh_ts.empty:
        beh_ts["label"] = beh_ts["answered_yes"].map({True: "Yes", False: "No", None: "Not tracked"})
        fig_beh = px.scatter(
            beh_ts, x="cycle_date", y="recovery_score", color="label",
            labels={"recovery_score": "Recovery %", "cycle_date": "Date", "label": label},
            color_discrete_map={"Yes": "#e53935", "No": "#43a047", "Not tracked": "#bdbdbd"},
        )
        fig_beh.update_layout(height=350, margin=dict(t=10, b=40))
        st.plotly_chart(fig_beh, use_container_width=True)

    st.divider()

# ===================================================================
# 11. ANOMALY ALERTS — recent outlier days
# ===================================================================
st.header("Anomaly Alerts")
st.markdown("Days where a key metric fell **outside 2 standard deviations** from the 30-day rolling baseline.")

anomaly_df = run_query("""
    WITH baselines AS (
        SELECT
            dc.cycle_date, dc.recovery_score, dc.hrv, dc.resting_hr, ss.sleep_efficiency,
            AVG(dc.recovery_score) OVER w30 AS r_avg, STDDEV(dc.recovery_score) OVER w30 AS r_std,
            AVG(dc.hrv) OVER w30 AS h_avg, STDDEV(dc.hrv) OVER w30 AS h_std,
            AVG(dc.resting_hr) OVER w30 AS rhr_avg, STDDEV(dc.resting_hr) OVER w30 AS rhr_std,
            AVG(ss.sleep_efficiency) OVER w30 AS e_avg, STDDEV(ss.sleep_efficiency) OVER w30 AS e_std
        FROM daily_cycles dc
        LEFT JOIN sleep_sessions ss ON ss.cycle_date = dc.cycle_date AND ss.is_nap = FALSE
        WINDOW w30 AS (ORDER BY dc.cycle_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
    )
    SELECT cycle_date, recovery_score, hrv, resting_hr, sleep_efficiency,
           ROUND((recovery_score - r_avg) / NULLIF(r_std, 0), 1) AS recovery_z,
           ROUND((hrv - h_avg) / NULLIF(h_std, 0), 1) AS hrv_z,
           ROUND((resting_hr - rhr_avg) / NULLIF(rhr_std, 0), 1) AS rhr_z,
           ROUND((sleep_efficiency - e_avg) / NULLIF(e_std, 0), 1) AS efficiency_z
    FROM baselines
    WHERE ABS(recovery_score - r_avg) > 2 * NULLIF(r_std, 0)
       OR ABS(hrv - h_avg) > 2 * NULLIF(h_std, 0)
       OR ABS(resting_hr - rhr_avg) > 2 * NULLIF(rhr_std, 0)
       OR ABS(sleep_efficiency - e_avg) > 2 * NULLIF(e_std, 0)
    ORDER BY cycle_date DESC
""")

if not anomaly_df.empty:
    anomaly_df.columns = ["Date", "Recovery", "HRV", "Resting HR", "Sleep Eff",
                          "Recovery Z", "HRV Z", "RHR Z", "Efficiency Z"]
    st.dataframe(anomaly_df, use_container_width=True, hide_index=True)
else:
    st.info("No anomalies detected in the selected date range.")

# ===================================================================
# Footer
# ===================================================================
st.divider()
st.caption("Built with PostgreSQL, Python, Streamlit & Plotly. All data retrieved via raw SQL queries.")
