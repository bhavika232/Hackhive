
from datetime import datetime, timezone

from app.database import init_db, insert_incident, get_incident
from app.schemas import (
    Category,
    ConfidenceStatus,
    IncidentCreate,
)


def test_save_and_retrieve_incident(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    original = IncidentCreate(
        camera_id="cam1",
        category=Category.CROWD_INCIDENT,
        summary="Several people gathered near the entrance.",
        confidence=0.85,
        confidence_status=ConfidenceStatus.NEEDS_REVIEW,
        start_video_s=12.5,
        start_wall_time=datetime.now(timezone.utc),
        track_ids=[1, 2, 3],
    )

    saved = insert_incident(original, db_path)
    retrieved = get_incident(saved.incident_id, db_path)

    assert retrieved is not None
    assert retrieved.camera_id == "cam1"
    assert retrieved.category == Category.CROWD_INCIDENT
    assert retrieved.track_ids == [1, 2, 3]
    assert retrieved.confidence == 0.85


def test_missing_incident_returns_none(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    assert get_incident(999, db_path) is None
