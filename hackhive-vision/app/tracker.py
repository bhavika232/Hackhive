import numpy as np

from app.detector import HF_FILE, HF_REPO, load_model, results_to_detections
from app.schemas import Detection


class ObjectTracker:
    """YOLO detection + ByteTrack. Make ONE tracker per video or camera."""

    def __init__(
        self,
        repo_id: str = HF_REPO,
        filename: str = HF_FILE,
        confidence_threshold: float = 0.35,
    ):
        self.model = load_model(repo_id, filename)
        self.confidence_threshold = confidence_threshold

    def update(self, frame: np.ndarray) -> list[Detection]:
        """Return detections for this frame. track_id is None until a track is confirmed."""
        results = self.model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.confidence_threshold,
            verbose=False,
        )
        return results_to_detections(results)