from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

class ConfidenceStatus(str, Enum):
    CONFIRMED = "confirmed"
    RULE_ONLY = "rule_only"
    NEEDS_REVIEW = "needs_review"
    UNCERTAIN = "uncertain"

class Category(str, Enum):
    PERSON_DOWN = "person_down"
    CROWD_INCIDENT = "crowd_incident"
    TAILGATING = "tailgating"
    CUSTOM_ALERT = "custom_alert"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"


class IncidentReviewUpdate(BaseModel):
    review_status: ReviewStatus


class VisionEventIngest(BaseModel):
    """HTTP payload sent by HackHive Vision for a classified event."""

    camera_id: str
    category: Category
    start_video_time_s: float
    end_video_time_s: float | None = None
    start_wall_time: datetime | None = None
    summary: str
    confidence: float = Field(ge=0, le=1)
    confidence_status: ConfidenceStatus
    keyframe_path: str
    track_ids: list[int] = Field(default_factory=list)
    event_type: str | None = None
    object_type: str | None = None
    region_id: str | None = None

class Detection(BaseModel):
    track_id: int | None = None
    class_name: str
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[float, float, float, float]


class IncidentCreate(BaseModel):
    camera_id: str
    category: Category
    summary: str
    confidence: float = Field(ge=0, le=1)
    confidence_status: ConfidenceStatus
    start_video_s: float
    end_video_s: float | None = None
    start_wall_time: datetime
    end_wall_time: datetime | None = None
    keyframe_path: str | None = None
    track_ids: list[int] = Field(default_factory=list)

class Incident(IncidentCreate):
    incident_id: int
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    occurrence_count: int = 1



class CustomRuleCreate(BaseModel):
    description: str


class CustomRule(BaseModel):
    rule_id: int
    description: str
    event_type: str
    region_id: str
    object_type: str
    enabled: bool
    created_at: str
