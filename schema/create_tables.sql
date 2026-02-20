-- ============================================================
-- Health Analytics Schema
-- Creates all tables for the Whoop biometric data pipeline.
-- Run this before loading data via etl/load_data.py.
-- ============================================================

-- Daily cycles: primary fact table, one row per day
CREATE TABLE IF NOT EXISTS daily_cycles (
    cycle_id    SERIAL PRIMARY KEY,
    cycle_date  DATE NOT NULL UNIQUE,
    cycle_start TIMESTAMP NOT NULL,
    cycle_end   TIMESTAMP,
    timezone    TEXT,
    recovery_score  NUMERIC,
    resting_hr      NUMERIC,
    hrv             NUMERIC,
    skin_temp       NUMERIC,
    blood_oxygen    NUMERIC,
    day_strain      NUMERIC,
    energy_burned   NUMERIC,
    max_hr          INTEGER,
    avg_hr          INTEGER
);

-- Sleep sessions: one row per sleep (including naps)
CREATE TABLE IF NOT EXISTS sleep_sessions (
    sleep_id            SERIAL PRIMARY KEY,
    cycle_date          DATE NOT NULL REFERENCES daily_cycles(cycle_date),
    sleep_onset         TIMESTAMP,
    wake_onset          TIMESTAMP,
    is_nap              BOOLEAN DEFAULT FALSE,
    sleep_performance   NUMERIC,
    respiratory_rate    NUMERIC,
    asleep_duration_min NUMERIC,
    in_bed_duration_min NUMERIC,
    light_sleep_min     NUMERIC,
    deep_sleep_min      NUMERIC,
    rem_sleep_min       NUMERIC,
    awake_duration_min  NUMERIC,
    sleep_need_min      NUMERIC,
    sleep_debt_min      NUMERIC,
    sleep_efficiency    NUMERIC,
    sleep_consistency   NUMERIC
);

-- Workouts: one row per workout session
CREATE TABLE IF NOT EXISTS workouts (
    workout_id      SERIAL PRIMARY KEY,
    cycle_date      DATE NOT NULL REFERENCES daily_cycles(cycle_date),
    workout_start   TIMESTAMP,
    workout_end     TIMESTAMP,
    duration_min    NUMERIC,
    activity_name   TEXT,
    activity_strain NUMERIC,
    energy_burned   NUMERIC,
    max_hr          INTEGER,
    avg_hr          INTEGER,
    hr_zone1_pct    NUMERIC,
    hr_zone2_pct    NUMERIC,
    hr_zone3_pct    NUMERIC,
    hr_zone4_pct    NUMERIC,
    hr_zone5_pct    NUMERIC
);

-- Journal entries: one row per question per day (long format)
CREATE TABLE IF NOT EXISTS journal_entries (
    journal_id   SERIAL PRIMARY KEY,
    cycle_date   DATE NOT NULL REFERENCES daily_cycles(cycle_date),
    question     TEXT NOT NULL,
    answered_yes BOOLEAN,
    notes        TEXT
);

-- The journal_pivot view is created dynamically by the ETL script
-- after loading data, since the set of questions varies per user.
