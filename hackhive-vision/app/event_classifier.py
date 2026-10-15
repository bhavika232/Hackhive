# app/event_classifier.py
from typing import Callable, Optional

from app import vlm_service
from app.event_rules import RuleHit, check_crowd, check_person_down
from app.schemas import Category, ConfidenceStatus, EventCandidate, FrameData


class EventClassifier:
    def __init__(
        self,
        cooldown_s: float = 30.0,
        verifier: Optional[Callable[[str, str], Optional[bool]]] = None,
        describer: Optional[Callable[[str], Optional[str]]] = None,
    ):
        self.cooldown_s = cooldown_s
        self.verifier = verifier or vlm_service.verify_event
        self.describer = describer or vlm_service.describe_frame
        self._last_emit: dict = {}  # (camera, category, track_ids) -> video time

    def _rule_hits(self, frame: FrameData, history: list[FrameData]) -> list[RuleHit]:
        hits = list(check_person_down(frame, history))
        crowd = check_crowd(frame, history)
        if crowd is not None:
            hits.append(crowd)
        return hits

    def classify(self, frame: FrameData, history: list[FrameData]) -> list[EventCandidate]:
        """history: previous FrameData for this camera, oldest to newest."""
        candidates = []
        for hit in self._rule_hits(frame, history):
            key = (frame.camera_id, hit.category, tuple(hit.track_ids))
            last = self._last_emit.get(key)
            if last is not None and frame.video_time_s - last < self.cooldown_s:
                continue  # same ongoing incident, skip the VLM call too
            self._last_emit[key] = frame.video_time_s

            try:
                agrees = self.verifier(frame.frame_path, hit.category.value)
            except Exception as e:
                print(f"[event_classifier] verifier failed: {e}")
                agrees = None

            if agrees is True:
                status, confidence = ConfidenceStatus.CONFIRMED, min(1.0, hit.score + 0.15)
            elif agrees is False:
                status, confidence = ConfidenceStatus.NEEDS_REVIEW, hit.score * 0.5
            else:
                status, confidence = ConfidenceStatus.RULE_ONLY, hit.score

            summary = hit.evidence
            if agrees is not False:
                try:
                    desc = self.describer(frame.frame_path)
                except Exception:
                    desc = None
                if desc:
                    summary = f"{hit.evidence}. Scene: {desc}"

            candidates.append(EventCandidate(
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
            ))
        return candidates