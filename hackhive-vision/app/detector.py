import numpy as np
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

from app.schemas import Detection

HF_REPO = "Ultralytics/YOLOv8"
HF_FILE = "yolov8n.pt"


def load_model(repo_id: str = HF_REPO, filename: str = HF_FILE) -> YOLO:
    """Download the weights from Hugging Face (cached after first time) and load."""
    return YOLO(hf_hub_download(repo_id=repo_id, filename=filename))


def results_to_detections(results) -> list[Detection]:
    """Convert Ultralytics results into the team's Detection objects."""
    detections = []

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = int(box.cls.item())
            x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
            track_id = int(box.id.item()) if box.id is not None else None

            detections.append(
                Detection(
                    track_id=track_id,
                    label=result.names[class_id],
                    confidence=float(box.conf.item()),
                    bbox=(x1, y1, x2, y2),
                )
            )

    return detections


class ObjectDetector:
    """Run YOLO object detection on single frames (no tracking)."""

    def __init__(
        self,
        repo_id: str = HF_REPO,
        filename: str = HF_FILE,
        confidence_threshold: float = 0.35,
    ):
        self.model = load_model(repo_id, filename)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Return detected objects for one BGR image."""
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            verbose=False,
        )
        return results_to_detections(results)

    def detect_people(self, frame: np.ndarray) -> list[Detection]:
        """Return only detections labelled as people."""
        return [d for d in self.detect(frame) if d.label == "person"]