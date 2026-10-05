import json
import sqlite3
from datetime import datetime, timezone

DB_PATH = "invoiceiq.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            original_json TEXT NOT NULL,
            corrected_json TEXT NOT NULL,
            needs_review INTEGER NOT NULL,
            saved_at TEXT NOT NULL
        )
        """
    )
    return conn


def save_invoice(file_name: str, original: dict, corrected: dict, needs_review: bool) -> int:
    conn = _connect()
    try:
        cursor = conn.execute(
            "INSERT INTO invoices (file_name, original_json, corrected_json, needs_review, saved_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                file_name,
                json.dumps(original),
                json.dumps(corrected),
                int(needs_review),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_invoices() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, file_name, original_json, corrected_json, needs_review, saved_at "
            "FROM invoices ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row[0],
            "file_name": row[1],
            "original": json.loads(row[2]),
            "corrected": json.loads(row[3]),
            "needs_review": bool(row[4]),
            "saved_at": row[5],
        }
        for row in rows
    ]