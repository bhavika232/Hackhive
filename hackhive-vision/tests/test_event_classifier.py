# tests/test_event_classifier.py
from app.schemas import FrameData, Detection, Category, ConfidenceStatus
from app.event_classifier import EventClassifier


def make_frame(t, bboxes):
    dets = [Detection(track_id=1 + i, label="person", confidence=0.9, bbox=b)
            for i, b in enumerate(bboxes)]
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=dets, person_count=len(dets))


STANDING = (100, 100, 150, 250)
LYING = (100, 200, 250, 250)
HISTORY = [make_frame(0, [STANDING]), make_frame(1, [LYING]), make_frame(2, [LYING])]
NOW = make_frame(3.5, [LYING])
describe = lambda path: "a person on the floor"


def run(verifier):
    clf = EventClassifier(verifier=verifier, describer=describe)
    return clf, clf.classify(NOW, HISTORY)


def test_vlm_agrees_is_confirmed():
    _, out = run(lambda p, c: True)
    assert out[0].category == Category.PERSON_DOWN
    assert out[0].confidence_status == ConfidenceStatus.CONFIRMED


def test_vlm_disagrees_needs_review():
    _, out = run(lambda p, c: False)
    assert out[0].confidence_status == ConfidenceStatus.NEEDS_REVIEW


def test_vlm_unclear_is_rule_only():
    _, out = run(lambda p, c: None)
    assert out[0].confidence_status == ConfidenceStatus.RULE_ONLY


def test_vlm_crash_does_not_break_pipeline():
    def boom(p, c):
        raise RuntimeError("model died")
    _, out = run(boom)
    assert out[0].confidence_status == ConfidenceStatus.RULE_ONLY


def test_cooldown_suppresses_repeat():
    clf, first = run(lambda p, c: True)
    again = clf.classify(make_frame(4.0, [LYING]), HISTORY + [NOW])
    assert len(first) == 1 and again == []