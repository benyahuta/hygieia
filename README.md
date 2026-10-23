# hygieia

Analyzing my own Whoop data with SQL. It loads Whoop's CSV exports into PostgreSQL and runs queries to figure out which habits actually affect my recovery and sleep.

The queries are in `queries/`. Some examples:

- which habits from the daily journal are linked to better or worse recovery
- whether today's strain predicts tomorrow's recovery
- how alcohol affects sleep, HRV, and resting heart rate
- rolling z-scores to flag unusual days
- recovery streaks and trends

There's also a Streamlit dashboard in `dashboard/` that shows the results.

## Running it

You need PostgreSQL and Python 3.9+. My data isn't included, but there's synthetic sample data in `data/sample/`.

```bash
pip install -r requirements.txt
python etl/load_data.py
psql health_analytics -f queries/01_recovery_drivers.sql
streamlit run dashboard/app.py
```
