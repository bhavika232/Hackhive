# app/schemas.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Category(str, Enum):
    PERSON_DOWN = "person_down"
    CROWD = "crowd_incident"
    TAILGATING = "tailgating"


class ConfidenceStatus(str, Enum):
    CONFIRMED = "confirmed"        # rule + VLM agree
    RULE_ONLY = "rule_only"        # rule fired, VLM disagreed or failed
    NEEDS_REVIEW = "needs_review"  # weak or ambiguous evidence


class Detection(BaseModel):
    """Shreya produces this, one per object per sampled frame."""
    track_id: Optional[int] = None
    label: str                     # "person", "backpack", ...
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


class FrameData(BaseModel):
    """Shreya -> Bhavika, one per sampled frame."""
    camera_id: str
    frame_index: int
    video_time_s: float            # seconds from video start
    wall_time: Optional[str] = None  # ISO 8601 if known, else None
    frame_path: str                # saved frame on disk
    width: int
    height: int
    detections: list[Detection]
    person_count: int


class EventCandidate(BaseModel):
    """Bhavika -> Sashia."""
    camera_id: str
    category: Category
    start_video_time_s: float
    end_video_time_s: Optional[float] = None
    start_wall_time: Optional[str] = None
    summary: str
    confidence: float
    confidence_status: ConfidenceStatus
    keyframe_path: str
    track_ids: list[int] = []


class Incident(EventCandidate):
    """Sashia stores this."""
    incident_id: int
    review_status: str = "unreviewed"  # unreviewed | confirmed | false_alarm