# tests/test_run_pipeline.py
from app.event_classifier import EventClassifier
from app.schemas import Detection, FrameData
from run_pipeline import run

STANDING = (100, 100, 150, 250)
LYING = (100, 200, 250, 250)


def make_frame(t, bbox):
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=[Detection(track_id=1, label="person", confidence=0.9, bbox=bbox)],
                     person_count=1)


def test_fall_sequence_produces_one_event():
    frames = [make_frame(0, STANDING)] + [make_frame(t / 2, LYING) for t in range(1, 9)]
    clf = EventClassifier(verifier=lambda p, c: True, describer=lambda p: "person on floor")
    events = []
    run(frames, clf, events.append)
    assert len(events) == 1  # cooldown stops repeat alerts for the same fall


def test_crashing_classifier_does_not_stop_run():
    class Boom:
        calls = 0

        def classify(self, frame, history):
            Boom.calls += 1
            raise RuntimeError("boom")

    frames = [make_frame(t, STANDING) for t in range(3)]
    run(frames, Boom(), lambda c: None)
    assert Boom.calls == 3