
from datetime import datetime

from app.database import insert_incident, list_custom_rules
from app.schemas import Category, ConfidenceStatus, IncidentCreate


def ingest_event(candidate):
    """Convert a vision event into a persisted backend incident."""

    category_value = getattr(candidate.category, "value", candidate.category)
    confidence_value = getattr(
        candidate.confidence_status,
        "value",
        candidate.confidence_status,
    )

    category_map = {
        "person_down": Category.PERSON_DOWN,
        "crowd_incident": Category.CROWD_INCIDENT,
        "crowd": Category.CROWD_INCIDENT,
        "tailgating": Category.TAILGATING,
    }

    confidence_map = {
        "confirmed": ConfidenceStatus.CONFIRMED,
        "rule_only": ConfidenceStatus.RULE_ONLY,
        "needs_review": ConfidenceStatus.NEEDS_REVIEW,
        "uncertain": ConfidenceStatus.UNCERTAIN,
    }

    category = category_map.get(str(category_value))
    confidence_status = confidence_map.get(str(confidence_value))

    if confidence_status is None:
        raise ValueError(
            f"Unsupported confidence status: {confidence_value}"
        )

    matching_rule = None

    event_type = getattr(candidate, "event_type", None)
    object_type = getattr(candidate, "object_type", None)
    region_id = getattr(candidate, "region_id", None)

    
    if str(category_value) == "tailgating":
        for rule in list_custom_rules(enabled=True):
            if (
                rule["event_type"] == "tailgating"
                and rule["object_type"] == "person"
            ):
                matching_rule = rule
                break

    elif event_type and object_type and region_id:
        for rule in list_custom_rules(enabled=True):
            if (
                rule["event_type"] == event_type
                and rule["object_type"] == object_type
                and rule["region_id"] == region_id
            ):
                matching_rule = rule
                break
    if matching_rule:
        category = Category.CUSTOM_ALERT
    elif category is None:
        raise ValueError(
            f"Unsupported incident category: {category_value}"
        )

    wall_time = candidate.start_wall_time

    if wall_time is None:
        wall_time = datetime.now()
    elif isinstance(wall_time, str):
        wall_time = datetime.fromisoformat(wall_time)

    summary = candidate.summary

    if matching_rule:
        summary = (
            f"Custom alert: {matching_rule['description']} "
            f"Original event: {candidate.summary}"
        )

    incident = IncidentCreate(
        camera_id=candidate.camera_id,
        category=category,
        summary=summary,
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

