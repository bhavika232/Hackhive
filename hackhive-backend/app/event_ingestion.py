
from datetime import datetime

from app.database import insert_incident
from app.schemas import (
    Category,
    ConfidenceStatus,
    IncidentCreate,
)


def ingest_event(candidate):
    """Convert a vision EventCandidate into a persisted backend incident."""

    category_value = getattr(candidate.category, "value", candidate.category)
    confidence_value = getattr(
        candidate.confidence_status,
        "value",
        candidate.confidence_status,
    )

    # Normalize category names from the vision pipeline.
    category_map = {
        "person_down": Category.PERSON_DOWN,
        "crowd_incident": Category.CROWD_INCIDENT,
        "crowd": Category.CROWD_INCIDENT,
        "tailgating": Category.TAILGATING,
    }

    # Preserve the vision team's confidence meaning.
    confidence_map = {
        "confirmed": ConfidenceStatus.CONFIRMED,
        "rule_only": ConfidenceStatus.RULE_ONLY,
        "needs_review": ConfidenceStatus.NEEDS_REVIEW,
        "uncertain": ConfidenceStatus.UNCERTAIN,
    }

    category = category_map.get(str(category_value))
    confidence_status = confidence_map.get(str(confidence_value))

    if category is None:
        raise ValueError(f"Unsupported incident category: {category_value}")

    if confidence_status is None:
        raise ValueError(
            f"Unsupported confidence status: {confidence_value}"
        )

    wall_time = candidate.start_wall_time
    if wall_time is None:
        wall_time = datetime.now()
    elif isinstance(wall_time, str):
        wall_time = datetime.fromisoformat(wall_time)

    incident = IncidentCreate(
        camera_id=candidate.camera_id,
        category=category,
        summary=candidate.summary,
        confidence=candidate.confidence,
        confidence_status=confidence_status,
        start_video_s=candidate.start_video_time_s,
        end_video_s=candidate.end_video_time_s,
        start_wall_time=wall_time,
        end_wall_time=None,
        keyframe_path=candidate.keyframe_path,
        track_ids=candidate.track_ids,
    )

    return insert_incident(incident)
