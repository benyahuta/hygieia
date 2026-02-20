# Health Analytics SQL Project

A personal health analytics platform that ingests Whoop biometric data, normalizes it into a relational PostgreSQL schema, and runs analytical SQL queries to surface insights about how daily behavioral choices impact physiological outcomes.

## Why This Project

I built this to demonstrate the same kind of analytical thinking that drives operational decision-making at scale — applied to a domain I care about personally. The core challenge is identical whether you're analyzing biometric recovery data or fleet telemetry: **take noisy, time-series sensor data, normalize it, and extract actionable signals through SQL.**

Parallels to fleet/operations analytics:
- **Time-series analysis** — rolling averages, anomaly detection, trend identification
- **Multi-dimensional correlation** — isolating which input variables drive which outcomes
- **Statistical rigor** — standard deviations, sample sizes, z-scores to distinguish signal from noise
- **Data pipeline reliability** — idempotent ETL, foreign key integrity, graceful NULL handling

## What's Inside

### SQL Queries (the showcase)

| Query | Description | Key Techniques |
|-------|-------------|----------------|
| `01_recovery_drivers.sql` | Behavioral impact on recovery — which habits help/hurt? | CTE, UNPIVOT, conditional aggregation, FILTER |
| `02_sleep_quality_trends.sql` | 7-day and 30-day rolling sleep analysis with anomaly flags | Window functions (AVG/STDDEV OVER ROWS BETWEEN) |
| `03_strain_recovery_correlation.sql` | Does today's strain predict tomorrow's recovery? | LEAD, NTILE quartile bucketing |
| `04_workout_performance.sql` | Workout quality by recovery tier (green/yellow/red) | CASE bucketing, ROLLUP |
| `05_alcohol_deep_analysis.sql` | Multi-layered alcohol impact: sleep, recovery, HRV, RHR | Multi-CTE chain, LEAD, FILTER |
| `06_optimal_conditions.sql` | Best combination of behaviors for peak recovery | GROUPING SETS, multi-table JOIN |
| `07_weekly_report.sql` | Automated week-over-week summary | DATE_TRUNC, LAG, ROLLUP |
| `08_anomaly_detection.sql` | Statistical outlier detection across all biometrics | 30-day rolling z-scores, window functions |
| `09_behavior_associations.sql` | Which behaviors co-occur? Market-basket analysis for habits | Self-join, lift calculation, co-occurrence rates |
| `10_recovery_momentum.sql` | Streak detection, trend direction, readiness forecast | Gap-and-island, LAG over rolling averages, CASE |
| `11_sleep_architecture.sql` | Which sleep stages predict next-day recovery? | NTILE bucketing, LEAD, UNION ALL |

### Data Pipeline

- **Source**: Whoop CSV exports (daily cycles, sleep sessions, workouts, journal entries)
- **ETL**: Python script that creates the database, builds the schema, loads data, and dynamically generates a pivoted journal view based on the actual questions found in the data
- **Schema**: 4 normalized tables with proper foreign keys + 1 dynamic view

### Dashboard

Streamlit app with:
- Overview cards with day-over-day deltas (recovery, HRV, RHR, strain, sleep)
- Recovery & HRV time series with 7-day rolling averages
- Recovery momentum panel — zone streaks, trend direction, color-coded timeline
- Behavioral impact table with horizontal bar chart (friendly column names)
- Behavior association explorer — co-occurrence lift analysis for any target behavior
- Stacked sleep stage breakdown (in hours)
- Sleep architecture analysis — deep/REM/duration tiers vs next-day recovery
- Strain vs next-day recovery scatter plot with OLS trendline
- Workout performance comparison by recovery tier
- Anomaly alerts table with z-scores
- Date range and journal behavior filters with sidebar navigation

## Getting Started

### Prerequisites
- PostgreSQL (local)
- Python 3.9+

### Data

Personal health data is **not included** in this repo. To run the project:

1. Export your data from the Whoop app (Settings > Data Export)
2. Unzip into `data/my_whoop_data_<date>/`
3. Update `DATA_DIR` in `etl/load_data.py` if needed

A `data/sample/` directory with synthetic example data is included for reference.

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the ETL pipeline (creates DB, schema, loads data, builds views)
python etl/load_data.py

# Run individual SQL queries
psql health_analytics -f queries/01_recovery_drivers.sql

# Launch the dashboard
streamlit run dashboard/app.py
```

## Project Structure

```
├── schema/create_tables.sql        # DDL for all tables
├── etl/load_data.py                # ETL pipeline
├── queries/                        # 11 analytical SQL queries
│   ├── 01_recovery_drivers.sql
│   ├── 02_sleep_quality_trends.sql
│   ├── 03_strain_recovery_correlation.sql
│   ├── 04_workout_performance.sql
│   ├── 05_alcohol_deep_analysis.sql
│   ├── 06_optimal_conditions.sql
│   ├── 07_weekly_report.sql
│   ├── 08_anomaly_detection.sql
│   ├── 09_behavior_associations.sql
│   ├── 10_recovery_momentum.sql
│   └── 11_sleep_architecture.sql
├── dashboard/app.py                # Streamlit dashboard
└── data/                           # Whoop CSV exports
```

## Tech Stack

- **PostgreSQL** — all analytics expressed as raw SQL
- **Python** — ETL only (pandas for CSV reading, psycopg2 for database interaction)
- **Streamlit + Plotly** — interactive dashboard with SQL-driven data retrieval
- **No ORMs** — raw SQL everywhere
