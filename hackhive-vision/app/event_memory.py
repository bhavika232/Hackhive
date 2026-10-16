
from app.schemas import EventCandidate


class EventMemory:
    """Groups repeated event candidates into ongoing incidents."""

    def __init__(self, gap_seconds: float = 10.0):
        
        self.gap_seconds = gap_seconds
        self.active_events: dict[tuple, EventCandidate] = {}
        self.completed_events: list[EventCandidate] = []

    def _event_key(self, event: EventCandidate) -> tuple:
        """Identify an event by camera, category, and tracked people."""
        return (
            event.camera_id,
            event.category,
            tuple(sorted(event.track_ids)),
        )

    def _can_merge(
        self,
        existing: EventCandidate,
        new: EventCandidate,
    ) -> bool:
        """Check whether two candidates belong to the same ongoing event."""
        if self._event_key(existing) != self._event_key(new):
            return False

        existing_end = (
            existing.end_video_time_s
            if existing.end_video_time_s is not None
            else existing.start_video_time_s
        )

        gap = new.start_video_time_s - existing_end
        return 0 <= gap <= self.gap_seconds

    def _merge(
        self,
        existing: EventCandidate,
        new: EventCandidate,
    ) -> EventCandidate:
        """Update an ongoing event with newer information."""
        return existing.model_copy(
            update={
                "end_video_time_s": (
                    new.end_video_time_s
                    if new.end_video_time_s is not None
                    else new.start_video_time_s
                ),
                "confidence": max(existing.confidence, new.confidence),
                "keyframe_path": new.keyframe_path,
                "summary": new.summary,
                "track_ids": sorted(
                    set(existing.track_ids + new.track_ids)
                ),
            }
        )

    def add_event(self, new: EventCandidate) -> None:
        """Merge a candidate into an active event or start a new one."""
        key = self._event_key(new)
        existing = self.active_events.get(key)

        if existing is not None and self._can_merge(existing, new):
            self.active_events[key] = self._merge(existing, new)
        else:
            if existing is not None:
                self.completed_events.append(existing)

            self.active_events[key] = new

    def flush(self, current_time_s: float) -> None:
        """Close active events that have been quiet for too long."""
        expired_keys = []

        for key, event in self.active_events.items():
            last_time = (
                event.end_video_time_s
                if event.end_video_time_s is not None
                else event.start_video_time_s
            )

            if current_time_s - last_time > self.gap_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            self.completed_events.append(self.active_events.pop(key))
