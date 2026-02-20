"""
ETL Pipeline for Whoop Health Analytics
========================================
Loads Whoop CSV exports into PostgreSQL, creates schema, and builds
a dynamic journal_pivot view based on the unique questions found in the data.

Usage:
    python etl/load_data.py
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_NAME = "health_analytics"
DB_USER = os.environ.get("PGUSER", os.environ.get("USER", "postgres"))
DB_HOST = os.environ.get("PGHOST", "localhost")
DB_PORT = os.environ.get("PGPORT", "5432")
DB_PASSWORD = os.environ.get("PGPASSWORD", "")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "my_whoop_data_2026_02_20",
)
SCHEMA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schema", "create_tables.sql",
)


def get_conn_params(dbname=DB_NAME):
    params = {"dbname": dbname, "user": DB_USER, "host": DB_HOST, "port": DB_PORT}
    if DB_PASSWORD:
        params["password"] = DB_PASSWORD
    return params


# ---------------------------------------------------------------------------
# 1. Create database if it doesn't exist
# ---------------------------------------------------------------------------
def create_database():
    conn = psycopg2.connect(**get_conn_params("postgres"))
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"Created database '{DB_NAME}'")
    else:
        print(f"Database '{DB_NAME}' already exists")
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# 2. Run schema DDL
# ---------------------------------------------------------------------------
def create_tables(conn):
    with open(SCHEMA_FILE, "r") as f:
        ddl = f.read()
    cur = conn.cursor()
    cur.execute(ddl)
    conn.commit()
    cur.close()
    print("Schema created (tables ready)")


# ---------------------------------------------------------------------------
# 3. Load CSVs
# ---------------------------------------------------------------------------
def parse_ts(series):
    """Parse timestamp columns, coercing blanks to NaT."""
    return pd.to_datetime(series, errors="coerce")


def load_daily_cycles(conn):
    df = pd.read_csv(os.path.join(DATA_DIR, "physiological_cycles.csv"))
    df["cycle_date"] = pd.to_datetime(df["Cycle start time"]).dt.date

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO daily_cycles (
                cycle_date, cycle_start, cycle_end, timezone,
                recovery_score, resting_hr, hrv, skin_temp, blood_oxygen,
                day_strain, energy_burned, max_hr, avg_hr
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (cycle_date) DO NOTHING
            """,
            (
                row["cycle_date"],
                pd.to_datetime(row["Cycle start time"]),
                pd.to_datetime(row["Cycle end time"]) if pd.notna(row["Cycle end time"]) else None,
                row["Cycle timezone"],
                row["Recovery score %"] if pd.notna(row.get("Recovery score %")) else None,
                row["Resting heart rate (bpm)"] if pd.notna(row.get("Resting heart rate (bpm)")) else None,
                row["Heart rate variability (ms)"] if pd.notna(row.get("Heart rate variability (ms)")) else None,
                row["Skin temp (celsius)"] if pd.notna(row.get("Skin temp (celsius)")) else None,
                row["Blood oxygen %"] if pd.notna(row.get("Blood oxygen %")) else None,
                row["Day Strain"] if pd.notna(row.get("Day Strain")) else None,
                row["Energy burned (cal)"] if pd.notna(row.get("Energy burned (cal)")) else None,
                int(row["Max HR (bpm)"]) if pd.notna(row.get("Max HR (bpm)")) else None,
                int(row["Average HR (bpm)"]) if pd.notna(row.get("Average HR (bpm)")) else None,
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    print(f"daily_cycles: {inserted} rows loaded")


def load_sleep_sessions(conn):
    df = pd.read_csv(os.path.join(DATA_DIR, "sleeps.csv"))
    df["cycle_date"] = pd.to_datetime(df["Cycle start time"]).dt.date

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        is_nap = str(row.get("Nap", "false")).strip().lower() == "true"
        cur.execute(
            """
            INSERT INTO sleep_sessions (
                cycle_date, sleep_onset, wake_onset, is_nap,
                sleep_performance, respiratory_rate,
                asleep_duration_min, in_bed_duration_min,
                light_sleep_min, deep_sleep_min, rem_sleep_min,
                awake_duration_min, sleep_need_min, sleep_debt_min,
                sleep_efficiency, sleep_consistency
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                row["cycle_date"],
                pd.to_datetime(row["Sleep onset"]) if pd.notna(row.get("Sleep onset")) else None,
                pd.to_datetime(row["Wake onset"]) if pd.notna(row.get("Wake onset")) else None,
                is_nap,
                row["Sleep performance %"] if pd.notna(row.get("Sleep performance %")) else None,
                row["Respiratory rate (rpm)"] if pd.notna(row.get("Respiratory rate (rpm)")) else None,
                row["Asleep duration (min)"] if pd.notna(row.get("Asleep duration (min)")) else None,
                row["In bed duration (min)"] if pd.notna(row.get("In bed duration (min)")) else None,
                row["Light sleep duration (min)"] if pd.notna(row.get("Light sleep duration (min)")) else None,
                row["Deep (SWS) duration (min)"] if pd.notna(row.get("Deep (SWS) duration (min)")) else None,
                row["REM duration (min)"] if pd.notna(row.get("REM duration (min)")) else None,
                row["Awake duration (min)"] if pd.notna(row.get("Awake duration (min)")) else None,
                row["Sleep need (min)"] if pd.notna(row.get("Sleep need (min)")) else None,
                row["Sleep debt (min)"] if pd.notna(row.get("Sleep debt (min)")) else None,
                row["Sleep efficiency %"] if pd.notna(row.get("Sleep efficiency %")) else None,
                row["Sleep consistency %"] if pd.notna(row.get("Sleep consistency %")) else None,
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    print(f"sleep_sessions: {inserted} rows loaded")


def load_workouts(conn):
    df = pd.read_csv(os.path.join(DATA_DIR, "workouts.csv"))
    df["cycle_date"] = pd.to_datetime(df["Cycle start time"]).dt.date

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO workouts (
                cycle_date, workout_start, workout_end, duration_min,
                activity_name, activity_strain, energy_burned,
                max_hr, avg_hr,
                hr_zone1_pct, hr_zone2_pct, hr_zone3_pct,
                hr_zone4_pct, hr_zone5_pct
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                row["cycle_date"],
                pd.to_datetime(row["Workout start time"]) if pd.notna(row.get("Workout start time")) else None,
                pd.to_datetime(row["Workout end time"]) if pd.notna(row.get("Workout end time")) else None,
                row["Duration (min)"] if pd.notna(row.get("Duration (min)")) else None,
                row["Activity name"] if pd.notna(row.get("Activity name")) else None,
                row["Activity Strain"] if pd.notna(row.get("Activity Strain")) else None,
                row["Energy burned (cal)"] if pd.notna(row.get("Energy burned (cal)")) else None,
                int(row["Max HR (bpm)"]) if pd.notna(row.get("Max HR (bpm)")) else None,
                int(row["Average HR (bpm)"]) if pd.notna(row.get("Average HR (bpm)")) else None,
                row["HR Zone 1 %"] if pd.notna(row.get("HR Zone 1 %")) else None,
                row["HR Zone 2 %"] if pd.notna(row.get("HR Zone 2 %")) else None,
                row["HR Zone 3 %"] if pd.notna(row.get("HR Zone 3 %")) else None,
                row["HR Zone 4 %"] if pd.notna(row.get("HR Zone 4 %")) else None,
                row["HR Zone 5 %"] if pd.notna(row.get("HR Zone 5 %")) else None,
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    print(f"workouts: {inserted} rows loaded")


def load_journal_entries(conn):
    df = pd.read_csv(os.path.join(DATA_DIR, "journal_entries.csv"))
    df["cycle_date"] = pd.to_datetime(df["Cycle start time"]).dt.date

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        answered = str(row.get("Answered yes", "")).strip().lower() == "true"
        cur.execute(
            """
            INSERT INTO journal_entries (cycle_date, question, answered_yes, notes)
            VALUES (%s, %s, %s, %s)
            """,
            (
                row["cycle_date"],
                row["Question text"],
                answered,
                row["Notes"] if pd.notna(row.get("Notes")) else None,
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    print(f"journal_entries: {inserted} rows loaded")


# ---------------------------------------------------------------------------
# 4. Build dynamic journal_pivot view
# ---------------------------------------------------------------------------
def make_column_alias(question):
    """Turn a journal question into a clean SQL column alias."""
    alias = question.lower()
    for ch in "?()/-":
        alias = alias.replace(ch, "")
    alias = alias.strip().replace(" ", "_")
    # Collapse multiple underscores
    while "__" in alias:
        alias = alias.replace("__", "_")
    return alias


def create_journal_pivot_view(conn):
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT question FROM journal_entries ORDER BY question")
    questions = [r[0] for r in cur.fetchall()]

    if not questions:
        print("No journal questions found — skipping pivot view")
        cur.close()
        return

    case_clauses = []
    for q in questions:
        alias = make_column_alias(q)
        case_clauses.append(
            f"    BOOL_OR(CASE WHEN question = '{q}' THEN answered_yes END) AS {alias}"
        )

    view_sql = "DROP VIEW IF EXISTS journal_pivot;\n"
    view_sql += "CREATE VIEW journal_pivot AS\nSELECT\n    cycle_date,\n"
    view_sql += ",\n".join(case_clauses)
    view_sql += "\nFROM journal_entries\nGROUP BY cycle_date;"

    cur.execute(view_sql)
    conn.commit()
    cur.close()
    print(f"journal_pivot view created with {len(questions)} question columns")


# ---------------------------------------------------------------------------
# 5. Verify row counts
# ---------------------------------------------------------------------------
def verify(conn):
    cur = conn.cursor()
    for table in ["daily_cycles", "sleep_sessions", "workouts", "journal_entries"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")
    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Health Analytics ETL Pipeline")
    print("=" * 60)

    # Step 1 — create database
    create_database()

    # Step 2 — connect and create schema
    conn = psycopg2.connect(**get_conn_params())
    create_tables(conn)

    # Step 3 — truncate for idempotent re-runs
    cur = conn.cursor()
    cur.execute("DROP VIEW IF EXISTS journal_pivot")
    for t in ["journal_entries", "workouts", "sleep_sessions", "daily_cycles"]:
        cur.execute(f"TRUNCATE {t} CASCADE")
    conn.commit()
    cur.close()
    print("Tables truncated for clean load")

    # Step 4 — load data (order matters for FK constraints)
    load_daily_cycles(conn)
    load_sleep_sessions(conn)
    load_workouts(conn)
    load_journal_entries(conn)

    # Step 5 — create pivot view
    create_journal_pivot_view(conn)

    # Step 6 — verify
    print("\nVerification:")
    verify(conn)

    conn.close()
    print("\nETL complete!")


if __name__ == "__main__":
    main()
