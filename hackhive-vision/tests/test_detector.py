import numpy as np

from app.detector import ObjectDetector
from app.tracker import ObjectTracker


def test_yolo_detects_objects():
    detector = ObjectDetector()

    # Blank image: only checks that inference runs and returns the right types.
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    detections = detector.detect(frame)

    assert isinstance(detections, list)
    for d in detections:
        assert 0.0 <= d.confidence <= 1.0
        assert len(d.bbox) == 4


def test_tracker_runs_on_blank_frames():
    tracker = ObjectTracker()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for _ in range(3):
        assert tracker.update(frame) == []