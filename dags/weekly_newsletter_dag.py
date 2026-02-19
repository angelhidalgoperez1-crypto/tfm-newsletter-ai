from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
import os
import yaml

# Load config
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

airflow_config = config.get("airflow", {})

# Parse start_date
start_date_str = airflow_config.get("start_date", "2025-01-01")
if isinstance(start_date_str, str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
else:
    start_date = start_date_str

DEFAULT_ARGS = {
    "owner": airflow_config.get("owner", "angel"),
    "depends_on_past": False,
    "retries": airflow_config.get("retries", 1),
    "retry_delay": timedelta(minutes=airflow_config.get("retry_delay_minutes", 10)),
}

with DAG(
    dag_id="weekly_newsletter",
    default_args=DEFAULT_ARGS,
    schedule_interval=airflow_config.get("schedule_interval", "0 6 * * MON"),
    start_date=start_date,
    catchup=airflow_config.get("catchup", False),
) as dag:

    def run_weekly():
        subprocess.run(["python", "/opt/project/scripts/run_weekly_pipeline.py"], check=True)

    t1 = PythonOperator(task_id="run_weekly_script", python_callable=run_weekly)
    t1
