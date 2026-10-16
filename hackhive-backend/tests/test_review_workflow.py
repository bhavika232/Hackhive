
from datetime import datetime, timezone

from app.database import (
    init_db,
    insert_incident,
    update_review_status,
)
from app.schemas import (
    Category,
    ConfidenceStatus,
    IncidentCreate,
    ReviewStatus,
)


def test_update_review_status(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    incident = insert_incident(
        IncidentCreate(
            camera_id="cam1",
            category=Category.CROWD_INCIDENT,
            summary="People gathered near entrance.",
            confidence=0.85,
            confidence_status=ConfidenceStatus.NEEDS_REVIEW,
            start_video_s=12.5,
            start_wall_time=datetime.now(timezone.utc),
        ),
        db_path,
    )

    updated = update_review_status(
        incident.incident_id,
        ReviewStatus.FALSE_POSITIVE,
        db_path,
    )

    assert updated is not None
    assert updated.review_status == ReviewStatus.FALSE_POSITIVE


def test_review_missing_incident(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    result = update_review_status(
        999999,
        ReviewStatus.TRUE_POSITIVE,
        db_path,
    )

    assert result is None
