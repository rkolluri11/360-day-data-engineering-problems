# 360-Day Data Engineering Problem Solving

One repo, five hard problems a day — the code behind a
[360-day Data Engineering & AI series](https://www.linkedin.com).

Every day ships **at least 5 problems** with full solutions and tests.
Each problem is a ladder: a beginner foothold first (the concept from
zero, in plain words), then the hardest realistic production version of
that problem. Every solution carries a plain-English explanation, and
each day carries one everyday analogy.

## The 360-day map

| Days | Block | Folder |
|------|-------|--------|
| 1–30 | Python | `day-01-…` → `day-30-…` |
| 31–60 | SQL | `day-31-…` → `day-60-…` |
| 61–90 | Snowflake | `day-61-…` → `day-90-…` |
| 91–120 | PySpark | `day-91-…` → `day-120-…` |
| 121–150 | Azure Event Hubs | `day-121-…` → `day-150-…` |
| 151–180 | Azure Data Factory | `day-151-…` → `day-180-…` |
| 181–210 | Azure Cosmos DB | `day-181-…` → `day-210-…` |
| 211–240 | Kafka / Confluent | `day-211-…` → `day-240-…` |
| 241–270 | Apache Airflow | `day-241-…` → `day-270-…` |
| 271–300 | Bash / Shell | `day-271-…` → `day-300-…` |
| 301–330 | AWS Data Engineering | `day-301-…` → `day-330-…` |
| 331–360 | Palantir Foundry | `day-331-…` → `day-360-…` |

Advanced blocks (Databricks, dbt, streaming, governance, GenAI DE…)
follow the same pattern after Day 360.

## How each day is laid out

```
day-01-python-foundations/
  README.md                  # the 5 problems, the analogy, the one-line lesson
  problem_01_<slug>.py       # statement in the docstring, solution below it
  problem_02_<slug>.py
  ...
  problem_05_<slug>.py
  tests/
    test_day_01.py           # pytest: every solution must pass
```

Run the tests for a day:

```bash
python -m pytest day-01-python-foundations/tests -q
```

## Profile

The profile README lives in the sibling repository named after the
GitHub username (e.g. `your-username/your-username`) and points here.

---
Built with care: each problem earned its place by being the kind of
thing that breaks a pipeline at 2 AM.
