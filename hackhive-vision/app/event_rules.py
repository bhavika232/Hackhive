# app/event_rules.py
from dataclasses import dataclass
from typing import Optional
from app.schemas import FrameData, Category


@dataclass
class RuleHit:
    category: Category
    track_ids: list[int]
    start_video_time_s: float
    evidence: str
    score: float  # rule strength 0-1, NOT a calibrated probability


def _is_horizontal(bbox, ratio: float) -> bool:
    x1, y1, x2, y2 = bbox
    h = y2 - y1
    return h > 0 and (x2 - x1) / h > ratio


def check_person_down(
    frame: FrameData,
    history: list[FrameData],
    ratio: float = 1.3,
    min_duration_s: float = 2.0,
) -> list[RuleHit]:
    """Tracked person's box stays wider than tall. Needs oldest-to-newest history."""
    frames = history + [frame]
    hits = []
    tracks = {d.track_id for d in frame.detections
              if d.label == "person" and d.track_id is not None}
    for tid in tracks:
        start, was_upright = None, False
        for f in reversed(frames):
            det = next((d for d in f.detections
                        if d.label == "person" and d.track_id == tid), None)
            if det is None:
                break
            if _is_horizontal(det.bbox, ratio):
                start = f.video_time_s
            else:
                was_upright = True
                break
        if start is not None and frame.video_time_s - start >= min_duration_s:
            hits.append(RuleHit(
                category=Category.PERSON_DOWN,
                track_ids=[tid],
                start_video_time_s=start,
                evidence=("was upright, then horizontal" if was_upright
                          else "horizontal for whole tracked history"),
                score=0.8 if was_upright else 0.5,
            ))
    return hits


def check_crowd(
    frame: FrameData,
    history: list[FrameData],
    threshold: int = 8,
    min_duration_s: float = 3.0,
) -> Optional[RuleHit]:
    """Person count stays at or above threshold for min_duration_s."""
    if frame.person_count < threshold:
        return None
    start = frame.video_time_s
    for f in reversed(history):
        if f.person_count < threshold:
            break
        start = f.video_time_s
    if frame.video_time_s - start < min_duration_s:
        return None
    return RuleHit(
        category=Category.CROWD,
        track_ids=[],
        start_video_time_s=start,
        evidence=f"{frame.person_count} people for {frame.video_time_s - start:.1f}s",
        score=0.7,
    )