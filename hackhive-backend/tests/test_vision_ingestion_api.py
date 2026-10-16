from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app import api, database, event_ingestion
from app.schemas import (
    Category,
    ConfidenceStatus,
    Incident,
    IncidentReviewUpdate,
    ReviewStatus,
    VisionEventIngest,
)


def test_vision_ingestion_route_is_registered():
    route = next(
        route for route in api.app.routes
        if getattr(route, "path", None) == "/ingest/vision-event"
    )
    assert "POST" in route.methods
    assert route.response_model is Incident


def test_vision_event_payload_maps_through_ingestion_adapter(monkeypatch):
    start_time = datetime(2026, 10, 16, 12, 30, tzinfo=timezone.utc)
    payload = VisionEventIngest(
        camera_id="cam1",
        category="person_down",
        start_video_time_s=12.5,
        end_video_time_s=14.0,
        start_wall_time=start_time.isoformat(),
        summary="Person fell near the entrance.",
        confidence=0.92,
        confidence_status="confirmed",
        keyframe_path="evidence/cam1/f000123.jpg",
        track_ids=[7],
    )
    expected = Incident(
        incident_id=41,
        camera_id="cam1",
        category=Category.PERSON_DOWN,
        summary=payload.summary,
        confidence=payload.confidence,
        confidence_status=ConfidenceStatus.CONFIRMED,
        start_video_s=12.5,
        end_video_s=14.0,
        start_wall_time=start_time,
        keyframe_path=payload.keyframe_path,
        track_ids=[7],
    )
    captured = {}

    def fake_ingest(candidate):
        captured["candidate"] = candidate
        return expected

    monkeypatch.setattr(api, "ingest_event", fake_ingest)
    result = api.ingest_vision_event(payload)

    assert result is expected
    assert captured["candidate"] is payload


def test_vision_event_payload_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        VisionEventIngest(
            camera_id="cam1",
            category="person_down",
            start_video_time_s=12.5,
            summary="Person fell.",
            confidence=1.5,
            confidence_status="confirmed",
            keyframe_path="evidence/frame.jpg",
        )


def test_incident_review_update_accepts_existing_review_statuses():
    update = IncidentReviewUpdate(review_status="false_positive")
    assert update.review_status == ReviewStatus.FALSE_POSITIVE


def test_vision_event_route_persists_incident(tmp_path, monkeypatch):
    db_path = tmp_path / "vision-events.db"
    database.init_db(db_path)
    monkeypatch.setattr(
        event_ingestion,
        "insert_incident",
        lambda incident: database.insert_incident(incident, db_path),
    )
    payload = VisionEventIngest(
        camera_id="cam1",
        category="tailgating",
        start_video_time_s=8.4,
        summary="Two people crossed the entrance together.",
        confidence=0.6,
        confidence_status="rule_only",
        keyframe_path="evidence/cam1/f000210.jpg",
        track_ids=[3, 8],
    )

    created = api.ingest_vision_event(payload)
    saved = database.get_incident(created.incident_id, db_path)

    assert saved is not None
    assert saved.camera_id == "cam1"
    assert saved.category == Category.TAILGATING
    assert saved.start_video_s == 8.4
    assert saved.track_ids == [3, 8]
    assert saved.summary == payload.summary
