
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from app.schemas import (
    Category,
    ConfidenceStatus,
    Incident,
    IncidentCreate,
    ReviewStatus,
)

DB_PATH = Path(__file__).resolve().parent.parent / "sentinel.db"


def get_connection(db_path=DB_PATH):
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path=DB_PATH):
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT NOT NULL,
                confidence REAL NOT NULL,
                confidence_status TEXT NOT NULL,
                start_video_s REAL NOT NULL,
                end_video_s REAL,
                start_wall_time TEXT NOT NULL,
                end_wall_time TEXT,
                keyframe_path TEXT,
                track_ids TEXT NOT NULL DEFAULT '[]',
                review_status TEXT NOT NULL DEFAULT 'unreviewed',
                occurrence_count INTEGER NOT NULL DEFAULT 1
            )
        """)


def insert_incident(incident: IncidentCreate, db_path=DB_PATH) -> Incident:
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO incidents (
                camera_id, category, summary, confidence,
                confidence_status, start_video_s, end_video_s,
                start_wall_time, end_wall_time, keyframe_path, track_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident.camera_id,
            incident.category.value,
            incident.summary,
            incident.confidence,
            incident.confidence_status.value,
            incident.start_video_s,
            incident.end_video_s,
            incident.start_wall_time.isoformat(),
            incident.end_wall_time.isoformat()
            if incident.end_wall_time else None,
            incident.keyframe_path,
            json.dumps(incident.track_ids),
        ))

        incident_id = cursor.lastrowid

    return get_incident(incident_id, db_path)


def get_incident(incident_id: int, db_path=DB_PATH):
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE incident_id = ?",
            (incident_id,),
        ).fetchone()

    if row is None:
        return None

    data = dict(row)
    data["start_wall_time"] = datetime.fromisoformat(
        data["start_wall_time"]
    )

    if data["end_wall_time"]:
        data["end_wall_time"] = datetime.fromisoformat(
            data["end_wall_time"]
        )

    data["track_ids"] = json.loads(data["track_ids"])
    data["category"] = Category(data["category"])
    data["confidence_status"] = ConfidenceStatus(
        data["confidence_status"]
    )
    data["review_status"] = ReviewStatus(data["review_status"])

    return Incident(**data)




def list_incidents(
    category: Category | None = None,
    review_status: ReviewStatus | None = None,
    camera_id: str | None = None,
    db_path=DB_PATH,
):
    query = "SELECT incident_id FROM incidents WHERE 1=1"
    params = []

    if category is not None:
        query += " AND category = ?"
        params.append(category.value)

    if review_status is not None:
        query += " AND review_status = ?"
        params.append(review_status.value)

    if camera_id is not None:
        query += " AND camera_id = ?"
        params.append(camera_id)

    query += " ORDER BY incident_id DESC"

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        get_incident(row["incident_id"], db_path)
        for row in rows
    ]


def update_review_status(
    incident_id: int,
    review_status: ReviewStatus,
    db_path=DB_PATH,
):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE incidents
            SET review_status = ?
            WHERE incident_id = ?
            """,
            (review_status.value, incident_id),
        )

        if cursor.rowcount == 0:
            return None

    return get_incident(incident_id, db_path)
