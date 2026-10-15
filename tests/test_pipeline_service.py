
from types import SimpleNamespace

from app import pipeline_service
from app import pipeline_service
from app.pipeline_service import PipelineService

class FakeClassifier:
    def __init__(self):
        self.calls = []

    def classify(self, frame, history):
        self.calls.append((frame, list(history)))
        return ["fake-candidate"]


def test_process_frame_classifies_and_ingests(monkeypatch):
    fake_classifier = FakeClassifier()
    saved = []

    monkeypatch.setattr(
        pipeline_service,
        "ingest_event",
        lambda candidate: saved.append(candidate) or "saved-incident",
    )

    frame = SimpleNamespace(
        camera_id="cam1",
        video_time_s=1.0,
    )

    service = PipelineService.__new__(PipelineService)
    service.classifier = fake_classifier
    service.history = {}

    result = service.process_frame(frame)

    assert result == ["saved-incident"]
    assert saved == ["fake-candidate"]
    assert fake_classifier.calls[0][0] is frame
    assert fake_classifier.calls[0][1] == []
    assert service.history["cam1"] == [frame]
