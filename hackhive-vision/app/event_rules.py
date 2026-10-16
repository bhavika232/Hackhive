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


def _aspect_ratio(bbox) -> float:
    x1, y1, x2, y2 = bbox
    height = y2 - y1
    return (x2 - x1) / height if height > 0 else 0.0


def check_person_down(
    frame: FrameData,
    history: list[FrameData],
    ratio: float = 1.3,
    min_duration_s: float = 2.0,
    max_observation_gap_s: float = 0.6,
    transition_window_s: float = 0.75,
    transition_min_duration_s: float = 0.5,
    transition_ratio: float = 1.5,
) -> list[RuleHit]:
    """Detect a sustained down posture or a persistent upright-to-down transition.

    Detection gaps are bridged only when the elapsed time between observations of
    the same track is within ``max_observation_gap_s``. The transition path allows
    a fall to be reported before the full sustained-posture duration, but requires
    a recent upright observation and a minimum period of horizontal observations.
    """
    frames = sorted(history + [frame], key=lambda item: item.video_time_s)
    hits = []
    tracks = {d.track_id for d in frame.detections
              if d.label == "person" and d.track_id is not None}
    for tid in tracks:
        observations = []
        for current in frames:
            detection = next((d for d in current.detections
                              if d.label == "person" and d.track_id == tid), None)
            if detection is not None:
                observations.append((current.video_time_s, detection))

        if not observations or observations[-1][0] != frame.video_time_s:
            continue
        if not _is_horizontal(observations[-1][1].bbox, ratio):
            continue

        horizontal_start_s = frame.video_time_s
        last_observation_s = frame.video_time_s
        upright_time_s = None
        for observation_s, detection in reversed(observations[:-1]):
            if last_observation_s - observation_s > max_observation_gap_s + 1e-9:
                break
            if not _is_horizontal(detection.bbox, ratio):
                upright_time_s = observation_s
                break

            horizontal_start_s = observation_s
            last_observation_s = observation_s

        horizontal_duration_s = frame.video_time_s - horizontal_start_s
        sustained = horizontal_duration_s >= min_duration_s
        transitioned = (
            upright_time_s is not None
            and horizontal_start_s - upright_time_s <= transition_window_s
            and horizontal_duration_s >= transition_min_duration_s
            and _aspect_ratio(observations[-1][1].bbox) >= transition_ratio
        )
        if sustained or transitioned:
            if transitioned:
                evidence = (
                    "upright-to-horizontal transition; horizontal for "
                    f"{horizontal_duration_s:.1f}s"
                )
            else:
                evidence = f"horizontal for {horizontal_duration_s:.1f}s"
            hits.append(RuleHit(
                category=Category.PERSON_DOWN,
                track_ids=[tid],
                start_video_time_s=horizontal_start_s,
                evidence=evidence,
                score=0.8 if upright_time_s is not None else 0.5,
            ))
    return hits


def check_crowd(
    frame: FrameData,
    history: list[FrameData],
    threshold: int = 8,
    min_duration_s: float = 3.0,
    max_observation_gap_s: float = 0.5,
    max_below_threshold_s: float = 0.5,
) -> Optional[RuleHit]:
    """Detect sustained crowding, tolerating brief count dips by elapsed time.

    Crowd size is a per-frame count, so track IDs do not need to persist. Counts
    below the threshold may be bridged for at most ``max_below_threshold_s``;
    larger gaps between sampled observations always break the run.
    """
    if frame.person_count < threshold:
        return None

    frames = sorted(history + [frame], key=lambda item: item.video_time_s)
    start = frame.video_time_s
    last_observation_s = frame.video_time_s
    last_crowded_s = frame.video_time_s
    for previous in reversed(frames[:-1]):
        if last_observation_s - previous.video_time_s > max_observation_gap_s + 1e-9:
            break
        last_observation_s = previous.video_time_s
        if previous.person_count >= threshold:
            start = previous.video_time_s
            last_crowded_s = previous.video_time_s
        elif last_crowded_s - previous.video_time_s > max_below_threshold_s + 1e-9:
            break

    if frame.video_time_s - start < min_duration_s:
        return None
    return RuleHit(
        category=Category.CROWD,
        track_ids=[],
        start_video_time_s=start,
        evidence=(
            f"at least {threshold} people for "
            f"{frame.video_time_s - start:.1f}s (brief count dips tolerated)"
        ),
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
