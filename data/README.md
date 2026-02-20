# Data

This project uses Whoop CSV exports as its data source. Personal health data is **not** included in the repository.

## Setup

1. Export your data from the [Whoop app](https://www.whoop.com/) (Settings > Data Export)
2. Unzip the export into this directory, e.g. `data/my_whoop_data_2026_02_20/`
3. Update the `DATA_DIR` path in `etl/load_data.py` if your folder name differs

## Expected Files

The ETL script expects these four CSVs in the data directory:

- `physiological_cycles.csv` — one row per day (recovery, HRV, strain, sleep summary)
- `sleeps.csv` — one row per sleep session (includes naps)
- `workouts.csv` — one row per workout
- `journal_entries.csv` — one row per journal question per day

## Sample Data

The `sample/` directory contains synthetic example data with the correct column structure. You can use it to test the pipeline:

```bash
# To test with sample data, temporarily point the ETL at it:
# In etl/load_data.py, change DATA_DIR to point to data/sample/
```
