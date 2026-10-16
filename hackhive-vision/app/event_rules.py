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




def _crossings(
    frames: list[FrameData],
    line: EntranceLine,
    max_observation_gap_s: float = 1.0,
) -> list[tuple[float, int, int]]:
    """Return crossings, tolerating short detection gaps for each track.

    The line stays in normalized coordinates and is projected into each frame's
    pixel space, matching both the rule and the debug overlay. A track's last
    observed side is retained across missing frames up to ``max_observation_gap_s``.
    """
    out = []
    last_observed: dict[int, tuple[float, int]] = {}

    for current in sorted(frames, key=lambda item: item.video_time_s):
        a = (line.x1 * current.width, line.y1 * current.height)
        b = (line.x2 * current.width, line.y2 * current.height)
        for detection in current.detections:
            tid = detection.track_id
            if detection.label != "person" or tid is None:
                continue

            point = _ref_point(detection.bbox, line.ref)
            orientation = _orient(a, b, point)
            side = 1 if orientation > 0 else -1 if orientation < 0 else 0
            previous = last_observed.get(tid)

            if previous is not None:
                previous_time, previous_side = previous
                gap = current.video_time_s - previous_time
                if gap > max_observation_gap_s:
                    previous = None
                elif side == 0:
                    # Keep the last non-zero side while a point lies on the line,
                    # so the following frame can complete the crossing.
                    last_observed[tid] = (current.video_time_s, previous_side)
                    continue
                elif previous_side != 0 and side != previous_side:
                    direction = 1 if side > 0 else -1
                    out.append((current.video_time_s, tid, direction))

            last_observed[tid] = (current.video_time_s, side)

    return out


def check_tailgating(
    frame: FrameData,
    history: list[FrameData],
    line: EntranceLine,
    window_s: float = 3.0,
    max_observation_gap_s: float = 1.0,
) -> Optional[RuleHit]:
    """Two different tracks cross the entrance line, same direction, within window_s."""
    frames = [
        f for f in history
        if f.video_time_s >= frame.video_time_s - window_s - max_observation_gap_s
    ] + [frame]
    recent = [
        crossing for crossing in _crossings(frames, line, max_observation_gap_s)
        if frame.video_time_s - window_s <= crossing[0] <= frame.video_time_s
    ]
    for direction in (1, -1):
        if line.entry_direction not in (None, direction):
            continue
        first_cross: dict[int, float] = {}
        for t, tid, d in sorted(recent):
            if d == direction and tid not in first_cross:
                first_cross[tid] = t
        times = sorted(first_cross.values())
        if len(times) >= 2 and times[-1] - times[0] <= window_s:
            return RuleHit(
                category=Category.TAILGATING,
                track_ids=sorted(first_cross),
                start_video_time_s=times[0],
                evidence=f"{len(first_cross)} people crossed entrance within {times[-1] - times[0]:.1f}s",
                score=0.6,
            )
    return None
