"""
Persistence: stores run metadata, data-quality results, and reconciliation
results in a local SQLite database so the dashboard can show history/trends,
not just the latest run.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone
import pandas as pd

DB_PATH = "recon_platform.db"


def get_connection(db_path: str = DB_PATH):
    return sqlite3.connect(db_path, check_same_thread=False)


def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            run_timestamp TEXT,
            file_a_name TEXT,
            file_b_name TEXT,
            key_column_a TEXT,
            key_column_b TEXT,
            compare_columns_json TEXT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            file_label TEXT,
            check_name TEXT,
            passed INTEGER,
            affected_row_count INTEGER,
            detail TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            key_value TEXT,
            status TEXT,
            mismatch_columns TEXT,
            row_json TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
    """)
    conn.commit()
    conn.close()


def save_run(
    file_a_name: str,
    file_b_name: str,
    key_column_a: str,
    key_column_b: str,
    compare_columns: list,
    dq_results_a: list,
    dq_results_b: list,
    reconciliation_df: pd.DataFrame,
    status: str = "success",
    db_path: str = DB_PATH,
) -> str:
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute(
        """INSERT INTO runs
           (run_id, run_timestamp, file_a_name, file_b_name, key_column_a, key_column_b, compare_columns_json, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, run_timestamp, file_a_name, file_b_name, key_column_a, key_column_b,
         json.dumps(compare_columns), status),
    )

    for label, dq_results in [("A", dq_results_a), ("B", dq_results_b)]:
        for r in dq_results:
            cur.execute(
                """INSERT INTO data_quality_results
                   (run_id, file_label, check_name, passed, affected_row_count, detail)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, label, r["check_name"], int(r["passed"]), r["affected_row_count"], r["detail"]),
            )

    for _, row in reconciliation_df.iterrows():
        row_dict = row.to_dict()
        cur.execute(
            """INSERT INTO reconciliation_results
               (run_id, key_value, status, mismatch_columns, row_json)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, str(row_dict.get("key")), row_dict.get("status"),
             row_dict.get("mismatch_columns"), json.dumps(row_dict, default=str)),
        )

    conn.commit()
    conn.close()
    return run_id


def load_run_history(db_path: str = DB_PATH) -> pd.DataFrame:
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM runs ORDER BY run_timestamp DESC", conn)
    conn.close()
    return df


def load_run_summary_counts(db_path: str = DB_PATH) -> pd.DataFrame:
    """One row per run_id with counts per status, for trend charts."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        """SELECT r.run_id, r.run_timestamp, rr.status, COUNT(*) as count
           FROM reconciliation_results rr
           JOIN runs r ON r.run_id = rr.run_id
           GROUP BY r.run_id, rr.status
           ORDER BY r.run_timestamp""",
        conn,
    )
    conn.close()
    return df


def load_reconciliation_results(run_id: str, db_path: str = DB_PATH) -> pd.DataFrame:
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM reconciliation_results WHERE run_id = ?", conn, params=(run_id,)
    )
    conn.close()
    return df


def load_dq_results(run_id: str, db_path: str = DB_PATH) -> pd.DataFrame:
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM data_quality_results WHERE run_id = ?", conn, params=(run_id,)
    )
    conn.close()
    return df
