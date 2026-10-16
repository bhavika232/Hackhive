
from dataclasses import dataclass
from typing import Callable, Optional

from app import vlm_service
from app.event_rules import (
    RuleHit,
    EntranceLine,
    check_crowd,
    check_person_down,
    check_tailgating,
    _is_horizontal,
)
from app.schemas import (
    Category,
    ConfidenceStatus,
    EventCandidate,
    FrameData,
)


@dataclass
class _PersonDownAlert:
    last_seen_s: float
    upright_since_s: Optional[float] = None


@dataclass
class _CrowdAlert:
    below_threshold_since_s: Optional[float] = None


class EventClassifier:
    def __init__(
        self,
        cooldown_s: float = 30.0,
        verifier: Optional[Callable[[str, str], Optional[bool]]] = None,
        describer: Optional[Callable[[str], Optional[str]]] = None,
        entrance_line: Optional[EntranceLine] = None,
        person_down_ratio: float = 1.3,
        person_down_max_observation_gap_s: float = 0.6,
        person_down_transition_ratio: float = 1.5,
        person_down_recovery_s: float = 0.5,
        person_down_track_expiry_s: float = 3.0,
        crowd_threshold: int = 8,
        crowd_min_duration_s: float = 3.0,
        crowd_max_observation_gap_s: float = 0.5,
        crowd_max_below_threshold_s: float = 0.5,
        crowd_recovery_s: float = 1.0,
    ):
        self.cooldown_s = cooldown_s
        self.verifier = verifier or vlm_service.verify_event
        self.describer = describer or vlm_service.describe_frame
        self.entrance_line = entrance_line
        self.person_down_ratio = person_down_ratio
        self.person_down_max_observation_gap_s = person_down_max_observation_gap_s
        self.person_down_transition_ratio = person_down_transition_ratio
        self.person_down_recovery_s = person_down_recovery_s
        self.person_down_track_expiry_s = person_down_track_expiry_s
        self.crowd_threshold = crowd_threshold
        self.crowd_min_duration_s = crowd_min_duration_s
        self.crowd_max_observation_gap_s = crowd_max_observation_gap_s
        self.crowd_max_below_threshold_s = crowd_max_below_threshold_s
        self.crowd_recovery_s = crowd_recovery_s
        self._last_emit: dict = {}
        self._active_person_down: dict[tuple[str, int], _PersonDownAlert] = {}
        self._active_crowd: dict[str, _CrowdAlert] = {}

    def _update_crowd_alert(self, frame: FrameData) -> None:
        state = self._active_crowd.get(frame.camera_id)
        if state is None:
            return
        if frame.person_count >= self.crowd_threshold:
            state.below_threshold_since_s = None
            return
        if state.below_threshold_since_s is None:
            state.below_threshold_since_s = frame.video_time_s
        elif frame.video_time_s - state.below_threshold_since_s >= self.crowd_recovery_s:
            del self._active_crowd[frame.camera_id]

    def _update_person_down_alerts(self, frame: FrameData) -> None:
        current = {
            detection.track_id: detection
            for detection in frame.detections
            if detection.label == "person" and detection.track_id is not None
        }
        now = frame.video_time_s

        for key, state in list(self._active_person_down.items()):
            camera_id, track_id = key
            if camera_id != frame.camera_id:
                continue

            detection = current.get(track_id)
            if detection is None:
                if now - state.last_seen_s > self.person_down_track_expiry_s:
                    del self._active_person_down[key]
                continue

            gap_s = now - state.last_seen_s
            if gap_s > self.person_down_track_expiry_s:
                del self._active_person_down[key]
                continue

            state.last_seen_s = now
            horizontal = _is_horizontal(detection.bbox, self.person_down_ratio)
            if horizontal:
                state.upright_since_s = None
                continue

            if gap_s > self.person_down_max_observation_gap_s:
                state.upright_since_s = now
            elif state.upright_since_s is None:
                state.upright_since_s = now

            if now - state.upright_since_s >= self.person_down_recovery_s:
                del self._active_person_down[key]

    def _rule_hits(
        self,
        frame: FrameData,
        history: list[FrameData],
    ) -> list[RuleHit]:
        hits = list(check_person_down(
            frame,
            history,
            ratio=self.person_down_ratio,
            max_observation_gap_s=self.person_down_max_observation_gap_s,
            transition_ratio=self.person_down_transition_ratio,
        ))

        crowd = check_crowd(
            frame,
            history,
            threshold=self.crowd_threshold,
            min_duration_s=self.crowd_min_duration_s,
            max_observation_gap_s=self.crowd_max_observation_gap_s,
            max_below_threshold_s=self.crowd_max_below_threshold_s,
        )
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

        self._update_person_down_alerts(frame)
        self._update_crowd_alert(frame)
        candidates = []

        for hit in self._rule_hits(frame, history):
            key = (
                frame.camera_id,
                hit.category,
                tuple(hit.track_ids),
            )

            if hit.category == Category.PERSON_DOWN:
                alert_key = (frame.camera_id, hit.track_ids[0])
                if alert_key in self._active_person_down:
                    continue
                self._active_person_down[alert_key] = _PersonDownAlert(
                    last_seen_s=frame.video_time_s,
                )
            elif hit.category == Category.CROWD:
                if frame.camera_id in self._active_crowd:
                    continue
                self._active_crowd[frame.camera_id] = _CrowdAlert()
            else:
                last = self._last_emit.get(key)
                if (
                    last is not None
                    and frame.video_time_s - last < self.cooldown_s
                ):
                    continue
                self._last_emit[key] = frame.video_time_s

            print(
                f"RULE_CANDIDATE category={hit.category.value} "
                f"t={hit.start_video_time_s:.2f}s tracks={hit.track_ids}"
            )
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
