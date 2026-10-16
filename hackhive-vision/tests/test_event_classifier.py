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
HISTORY = [make_frame(0, [STANDING])] + [
    make_frame(t, [LYING]) for t in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
]
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


def test_person_down_emits_once_until_recovery_then_can_alert_again():
    clf = EventClassifier(verifier=lambda _path, _category: None, describer=lambda _path: None)
    first = clf.classify(NOW, HISTORY)
    still_down = make_frame(4.0, [LYING])
    repeated = clf.classify(still_down, HISTORY + [NOW])
    assert len(first) == 1
    assert repeated == []

    upright_1 = make_frame(4.5, [STANDING])
    upright_2 = make_frame(5.0, [STANDING])
    clf.classify(upright_1, HISTORY + [NOW, still_down])
    clf.classify(upright_2, HISTORY + [NOW, still_down, upright_1])
    down_1 = make_frame(5.1, [LYING])
    down_2 = make_frame(5.6, [LYING])
    clf.classify(down_1, HISTORY + [NOW, still_down, upright_1, upright_2])
    after_recovery = clf.classify(
        down_2,
        HISTORY + [NOW, still_down, upright_1, upright_2, down_1],
    )
    assert len(after_recovery) == 1
    assert after_recovery[0].category == Category.PERSON_DOWN


def test_person_down_latch_expires_after_track_loss():
    clf = EventClassifier(verifier=lambda _path, _category: None, describer=lambda _path: None)
    assert len(clf.classify(NOW, HISTORY)) == 1
    missing = make_frame(7.0, [])
    assert clf.classify(missing, HISTORY + [NOW]) == []
    upright = make_frame(7.1, [STANDING])
    down_1 = make_frame(7.2, [LYING])
    down_2 = make_frame(7.7, [LYING])
    clf.classify(upright, [missing])
    clf.classify(down_1, [missing, upright])
    after_expiry = clf.classify(down_2, [missing, upright, down_1])
    assert len(after_expiry) == 1


def test_crowd_emits_once_until_sustained_recovery_then_can_alert_again():
    clf = EventClassifier(
        verifier=lambda _path, _category: None,
        describer=lambda _path: None,
        crowd_min_duration_s=1.0,
    )

    def crowd(t, count=8):
        return make_frame(t, [STANDING] * count)

    # Crowd duration is reached at 1s.
    history = [crowd(0.0), crowd(0.5), crowd(1.0)]
    first = clf.classify(crowd(1.5), history)
    again = clf.classify(crowd(2.0), history + [crowd(1.5)])
    assert len(first) == 1 and first[0].category == Category.CROWD
    assert again == []

    below_1 = make_frame(2.5, [STANDING] * 7)
    below_2 = make_frame(3.5, [STANDING] * 7)
    clf.classify(below_1, history + [crowd(1.5), crowd(2.0)])
    clf.classify(below_2, [below_1])

    new_history = [crowd(t) for t in (4.0, 4.5, 5.0)]
    second = clf.classify(crowd(5.5), new_history)
    assert len(second) == 1 and second[0].category == Category.CROWD
