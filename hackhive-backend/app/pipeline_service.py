
from app.event_ingestion import ingest_event


class PipelineService:
    def __init__(self, classifier):
        self.classifier = classifier
        self.history: dict[str, list] = {}

    def process_frame(self, frame) -> list:
        """Classify a frame and persist generated event candidates."""
        camera_history = self.history.setdefault(frame.camera_id, [])

        candidates = self.classifier.classify(frame, camera_history)

        saved_incidents = [
            ingest_event(candidate)
            for candidate in candidates
        ]

        camera_history.append(frame)

        cutoff = frame.video_time_s - 15.0
        self.history[frame.camera_id] = [
            item for item in camera_history
            if item.video_time_s >= cutoff
        ]

        return saved_incidents
