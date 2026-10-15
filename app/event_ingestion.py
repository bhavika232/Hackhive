
from datetime import datetime

from app.database import insert_incident
from app.schemas import IncidentCreate


def ingest_event(candidate):
    """Convert an EventCandidate into a persisted backend incident."""

    wall_time = candidate.start_wall_time

    if wall_time is None:
        wall_time = datetime.now()
    elif isinstance(wall_time, str):
        wall_time = datetime.fromisoformat(wall_time)

    incident = IncidentCreate(
        camera_id=candidate.camera_id,
        category=candidate.category,
        summary=candidate.summary,
        confidence=candidate.confidence,
        confidence_status=candidate.confidence_status,
        start_video_s=candidate.start_video_time_s,
        end_video_s=candidate.end_video_time_s,
        start_wall_time=wall_time,
        keyframe_path=candidate.keyframe_path,
        track_ids=candidate.track_ids,
    )

    return insert_incident(incident)

