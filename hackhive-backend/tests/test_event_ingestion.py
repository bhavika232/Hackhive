
from types import SimpleNamespace
from datetime import datetime

from app import event_ingestion
from app.schemas import Category, ConfidenceStatus, Incident


def test_ingest_event_converts_and_saves_candidate(monkeypatch):
    candidate = SimpleNamespace(
        camera_id="cam1",
        category=Category.CROWD_INCIDENT,
        summary="Crowd gathering detected",
        confidence=0.91,
        confidence_status=ConfidenceStatus.CONFIRMED,
        start_video_time_s=12.5,
        end_video_time_s=None,
        start_wall_time="2026-10-16T01:00:00",
        keyframe_path="frames/cam1.jpg",
        track_ids=[1, 2, 3],
    )

    captured = {}

    def fake_insert_incident(incident):
        captured["incident"] = incident
        return incident

    monkeypatch.setattr(
        event_ingestion,
        "insert_incident",
        fake_insert_incident,
    )

    result = event_ingestion.ingest_event(candidate)

    saved = captured["incident"]
    assert saved.camera_id == "cam1"
    assert saved.category == Category.CROWD_INCIDENT
    assert saved.confidence_status == ConfidenceStatus.CONFIRMED
    assert saved.start_video_s == 12.5
    assert saved.start_wall_time == datetime.fromisoformat(
        "2026-10-16T01:00:00"
    )
    assert saved.track_ids == [1, 2, 3]
    assert result is saved
    
    
def test_tailgating_custom_rule_matches_event(monkeypatch):
    candidate = SimpleNamespace(
        camera_id="cam1",
        category=Category.TAILGATING,
        summary="Tailgating detected",
        confidence=0.9,
        confidence_status=ConfidenceStatus.CONFIRMED,
        start_video_time_s=15.0,
        end_video_time_s=None,
        start_wall_time="2026-10-17T01:00:00",
        keyframe_path="frames/cam1.jpg",
        track_ids=[1, 2],
        event_type=None,
        object_type=None,
        region_id=None,
    )

    monkeypatch.setattr(
        event_ingestion,
        "list_custom_rules",
        lambda enabled=True: [{
            "event_type": "tailgating",
            "object_type": "person",
            "region_id": "any",
            "description": "Alert me when tailgating occurs.",
            "enabled": True,
        }],
    )

    captured = {}

    def fake_insert_incident(incident):
        captured["incident"] = incident
        return incident

    monkeypatch.setattr(
        event_ingestion,
        "insert_incident",
        fake_insert_incident,
    )

    result = event_ingestion.ingest_event(candidate)

    assert result.category == Category.CUSTOM_ALERT
    assert result.summary.startswith("Custom alert:")



