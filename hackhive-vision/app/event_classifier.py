
from typing import Callable, Optional

from app import vlm_service
from app.event_rules import (
    RuleHit,
    EntranceLine,
    check_crowd,
    check_person_down,
    check_tailgating,
)
from app.schemas import (
    Category,
    ConfidenceStatus,
    EventCandidate,
    FrameData,
)


class EventClassifier:
    def __init__(
        self,
        cooldown_s: float = 30.0,
        verifier: Optional[Callable[[str, str], Optional[bool]]] = None,
        describer: Optional[Callable[[str], Optional[str]]] = None,
        entrance_line: Optional[EntranceLine] = None,
    ):
        self.cooldown_s = cooldown_s
        self.verifier = verifier or vlm_service.verify_event
        self.describer = describer or vlm_service.describe_frame
        self.entrance_line = entrance_line
        self._last_emit: dict = {}

    def _rule_hits(
        self,
        frame: FrameData,
        history: list[FrameData],
    ) -> list[RuleHit]:
        hits = list(check_person_down(frame, history))

        crowd = check_crowd(frame, history)
        if crowd is not None:
            hits.append(crowd)

        if self.entrance_line is not None:
            tail = check_tailgating(
                frame,
                history,
                self.entrance_line,
            )
            if tail is not None:
                hits.append(tail)

        return hits

    def classify(
        self,
        frame: FrameData,
        history: list[FrameData],
    ) -> list[EventCandidate]:
        """Classify events using rules and optional VLM verification."""

        candidates = []

        for hit in self._rule_hits(frame, history):
            key = (
                frame.camera_id,
                hit.category,
                tuple(hit.track_ids),
            )

            last = self._last_emit.get(key)
            if (
                last is not None
                and frame.video_time_s - last < self.cooldown_s
            ):
                continue

            self._last_emit[key] = frame.video_time_s

            try:
                agrees = self.verifier(
                    frame.frame_path,
                    hit.category.value,
                )
            except Exception as e:
                print(f"[event_classifier] verifier failed: {e}")
                agrees = None

            if agrees is True:
                status = ConfidenceStatus.CONFIRMED
                confidence = min(1.0, hit.score + 0.15)
            elif agrees is False:
                status = ConfidenceStatus.NEEDS_REVIEW
                confidence = hit.score * 0.5
            else:
                status = ConfidenceStatus.RULE_ONLY
                confidence = hit.score

            summary = hit.evidence

            if agrees is not False:
                try:
                    desc = self.describer(frame.frame_path)
                except Exception:
                    desc = None

                if desc:
                    summary = f"{hit.evidence}. Scene: {desc}"

            candidates.append(
                EventCandidate(
                    camera_id=frame.camera_id,
                    category=hit.category,
                    start_video_time_s=hit.start_video_time_s,
                    end_video_time_s=None,
                    start_wall_time=frame.wall_time,
                    summary=summary,
                    confidence=round(confidence, 2),
                    confidence_status=status,
                    keyframe_path=frame.frame_path,
                    track_ids=hit.track_ids,
                )
            )

        return candidates
