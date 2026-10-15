# tests/test_event_rules.py
from app.schemas import FrameData, Detection
from app.event_rules import check_person_down, check_crowd


def make_frame(t, bboxes, tid_start=1):
    dets = [Detection(track_id=tid_start + i, label="person", confidence=0.9, bbox=b)
            for i, b in enumerate(bboxes)]
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=dets, person_count=len(dets))


STANDING = (100, 100, 150, 250)   # w=50, h=150
LYING = (100, 200, 250, 250)      # w=150, h=50


def test_fall_detected():
    history = [make_frame(0, [STANDING]), make_frame(1, [LYING]),
               make_frame(2, [LYING])]
    hits = check_person_down(make_frame(3.5, [LYING]), history)
    assert len(hits) == 1 and hits[0].score == 0.8


def test_standing_no_alert():
    history = [make_frame(t, [STANDING]) for t in range(4)]
    assert check_person_down(make_frame(4, [STANDING]), history) == []


def test_too_brief_no_alert():
    history = [make_frame(0, [STANDING])]
    assert check_person_down(make_frame(0.5, [LYING]), history) == []


def test_crowd():
    many = [STANDING] * 9
    history = [make_frame(t, many) for t in range(4)]
    assert check_crowd(make_frame(4, many), history) is not None


def test_small_group_no_crowd():
    few = [STANDING] * 3
    history = [make_frame(t, few) for t in range(4)]
    assert check_crowd(make_frame(4, few), history) is None