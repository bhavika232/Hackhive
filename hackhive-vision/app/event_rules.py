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


@dataclass
class EntranceLine:
    """Doorway line in normalized 0-1 coordinates (resolution independent)."""
    x1: float
    y1: float
    x2: float
    y2: float
    entry_direction: Optional[int] = None  # +1 / -1 = count one direction only, None = either
    ref: str = "center"  # which box point must cross the line: "center" | "head" | "foot"
    

def _orient(o, u, v) -> float:
    return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])


def _ref_point(bbox, ref: str) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    if ref == "foot":
        return (cx, y2)
    if ref == "head":
        return (cx, y1)
    return (cx, (y1 + y2) / 2)


def _crossings(frames: list[FrameData], line: EntranceLine) -> list[tuple[float, int, int]]:
    """(time, track_id, direction) for every person whose reference point crossed the line."""
    w, h = frames[-1].width, frames[-1].height
    a, b = (line.x1 * w, line.y1 * h), (line.x2 * w, line.y2 * h)
    out = []
    for prev, cur in zip(frames, frames[1:]):
        prev_pts = {d.track_id: _ref_point(d.bbox, line.ref) for d in prev.detections
                    if d.label == "person" and d.track_id is not None}
        for d in cur.detections:
            if d.label != "person" or d.track_id not in prev_pts:
                continue
            p, q = prev_pts[d.track_id], _ref_point(d.bbox, line.ref)
            if _orient(a, b, p) * _orient(a, b, q) < 0 and _orient(p, q, a) * _orient(p, q, b) < 0:
                out.append((cur.video_time_s, d.track_id, 1 if _orient(a, b, q) > 0 else -1))
    return out

def check_tailgating(
    frame: FrameData,
    history: list[FrameData],
    line: EntranceLine,
    window_s: float = 3.0,
) -> Optional[RuleHit]:
    """Two different tracks cross the entrance line, same direction, within window_s."""
    frames = [f for f in history if f.video_time_s >= frame.video_time_s - window_s - 2.0] + [frame]
    recent = [c for c in _crossings(frames, line) if c[0] >= frame.video_time_s - window_s]
    for direction in (1, -1):
        if line.entry_direction not in (None, direction):
            continue
        first_cross: dict[int, float] = {}
        for t, tid, d in sorted(recent):
            if d == direction and tid not in first_cross:
                first_cross[tid] = t
        if len(first_cross) >= 2:
            times = sorted(first_cross.values())
            return RuleHit(
                category=Category.TAILGATING,
                track_ids=sorted(first_cross),
                start_video_time_s=times[0],
                evidence=f"{len(first_cross)} people crossed entrance within {times[-1] - times[0]:.1f}s",
                score=0.6,
            )
    return None