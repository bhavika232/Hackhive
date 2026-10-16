
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import Category, ConfidenceStatus, IncidentCreate


def test_valid_incident():
    incident = IncidentCreate(
        camera_id="cam1",
        category=Category.CROWD_INCIDENT,
        summary="Several people gathered near the entrance.",
        confidence=0.85,
        confidence_status=ConfidenceStatus.NEEDS_REVIEW,
        start_video_s=12.5,
        start_wall_time=datetime.now(timezone.utc),
    )

    assert incident.camera_id == "cam1"
    assert incident.confidence == 0.85


def test_invalid_confidence():
    with pytest.raises(ValidationError):
        IncidentCreate(
            camera_id="cam1",
            category=Category.PERSON_DOWN,
            summary="Possible person-down event.",
            confidence=1.5,
            confidence_status=ConfidenceStatus.UNCERTAIN,
            start_video_s=12.5,
            start_wall_time=datetime.now(timezone.utc),
        )
