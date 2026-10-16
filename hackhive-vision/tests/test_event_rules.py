# tests/test_event_rules.py
from app.schemas import FrameData, Detection
from app.event_rules import (
    EntranceLine,
    _crossings,
    check_crowd,
    check_person_down,
    check_tailgating,
)

def make_frame(t, bboxes, tid_start=1):
    dets = [Detection(track_id=tid_start + i, label="person", confidence=0.9, bbox=b)
            for i, b in enumerate(bboxes)]
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=dets, person_count=len(dets))


STANDING = (100, 100, 150, 250)   # w=50, h=150
LYING = (100, 200, 250, 250)      # w=150, h=50


def test_fall_detected():
    history = [make_frame(0, [STANDING])] + [
        make_frame(t, [LYING]) for t in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
    ]
    hits = check_person_down(make_frame(3.5, [LYING]), history)
    assert len(hits) == 1 and hits[0].score == 0.8


def test_sustained_fall_bridges_short_timestamp_gaps():
    history = [
        make_frame(0.0, [STANDING]),
        make_frame(0.1, [LYING]),
        make_frame(0.5, [LYING]),  # 0.4s observation gap is within tolerance.
        make_frame(1.0, [LYING]),
        make_frame(1.5, [LYING]),
        make_frame(2.1, [LYING]),  # 0.6s gap is also within tolerance.
    ]
    hits = check_person_down(make_frame(2.5, [LYING]), history)
    assert len(hits) == 1
    assert hits[0].category.value == "person_down"
    assert hits[0].start_video_time_s == 0.1


def test_standing_no_alert():
    history = [make_frame(t, [STANDING]) for t in range(4)]
    assert check_person_down(make_frame(4, [STANDING]), history) == []


def test_too_brief_no_alert():
    history = [make_frame(0, [STANDING])]
    assert check_person_down(make_frame(0.5, [LYING]), history) == []


def test_person_down_duration_resets_after_detection_gap():
    history = [
        make_frame(0.0, [STANDING]),
        make_frame(1.0, [LYING]),
        make_frame(2.0, [LYING]),
        make_frame(2.1, []),  # A missed detection breaks the continuous run.
        make_frame(2.2, [LYING]),
    ]
    assert check_person_down(make_frame(4.1, [LYING]), history) == []


def test_brief_upright_to_horizontal_transition_needs_strong_horizontal_shape():
    medium_horizontal = (100, 100, 240, 200)  # ratio 1.4: horizontal, below transition gate.
    history = [make_frame(0.0, [STANDING]), make_frame(0.1, [medium_horizontal])]
    assert check_person_down(
        make_frame(0.8, [medium_horizontal]),
        history,
    ) == []


def test_previous_upright_track_does_not_seed_a_new_track():
    history = [make_frame(0.0, [STANDING], tid_start=1)]
    history.append(make_frame(1.0, [STANDING], tid_start=1))
    history.append(make_frame(2.0, [LYING], tid_start=2))
    assert check_person_down(
        make_frame(2.7, [LYING], tid_start=2),
        history,
    ) == []


def test_crowd():
    many = [STANDING] * 9
    history = [make_frame(t / 2, many) for t in range(7)]
    assert check_crowd(make_frame(3.5, many), history) is not None


def test_small_group_no_crowd():
    few = [STANDING] * 3
    history = [make_frame(t, few) for t in range(4)]
    assert check_crowd(make_frame(4, few), history) is None


def crowd_frame(t, count, tid_start):
    return make_frame(t, [STANDING] * count, tid_start=tid_start)


def test_crowd_needs_threshold_for_full_duration_not_one_frame_spike():
    history = [crowd_frame(t, 7, 100 + t * 20) for t in (0, 1, 2)]
    spike = crowd_frame(2.5, 8, 200)
    assert check_crowd(spike, history) is None
    assert check_crowd(crowd_frame(3, 8, 300), history + [spike]) is None


def test_crowd_bridges_brief_below_threshold_dip_by_timestamp():
    history = [
        crowd_frame(0.0, 8, 0),
        crowd_frame(0.5, 8, 20),
        crowd_frame(1.0, 7, 40),  # 0.5s count dip is tolerated.
        crowd_frame(1.5, 8, 60),
        crowd_frame(2.0, 8, 80),
        crowd_frame(2.5, 8, 100),
    ]
    hit = check_crowd(crowd_frame(3.0, 8, 120), history)
    assert hit is not None
    assert hit.start_video_time_s == 0.0
    assert "brief count dips tolerated" in hit.evidence


def test_crowd_long_count_dip_resets_duration():
    history = [
        crowd_frame(0.0, 8, 0),
        crowd_frame(0.5, 8, 20),
        crowd_frame(1.0, 7, 40),
        crowd_frame(1.5, 7, 60),
        crowd_frame(2.0, 8, 80),
        crowd_frame(2.5, 8, 100),
    ]
    assert check_crowd(crowd_frame(3.0, 8, 120), history) is None


def test_crowd_long_observation_gap_resets_duration():
    history = [crowd_frame(t, 8, i * 20) for i, t in enumerate((0.0, 0.5, 1.0, 3.0, 3.5))]
    assert check_crowd(crowd_frame(4.0, 8, 120), history) is None


def test_crowd_does_not_require_persistent_track_ids():
    times = (0, 0.5, 1, 1.5, 2, 2.5, 3)
    history = [crowd_frame(t, 8, i * 20) for i, t in enumerate(times)]
    hit = check_crowd(crowd_frame(3.5, 8, 1000), history)
    assert hit is not None


def test_crowd_normal_scene_below_threshold_never_hits():
    history = [crowd_frame(t, 4, t * 20) for t in range(5)]
    assert check_crowd(crowd_frame(5, 4, 200), history) is None

LINE = EntranceLine(x1=0.5, y1=0.0, x2=0.5, y2=1.0)  # vertical line at x=320 on 640x480


def tracks_frame(t, positions):
    dets = [Detection(track_id=tid, label="person", confidence=0.9,
                      bbox=(x - 25, 100, x + 25, 250)) for tid, x in positions.items()]
    return FrameData(camera_id="cam1", frame_index=int(t * 5), video_time_s=t,
                     frame_path="x.jpg", width=640, height=480,
                     detections=dets, person_count=len(dets))


def test_tailgating_two_same_direction():
    history = [tracks_frame(0, {1: 300}), tracks_frame(0.5, {1: 340, 2: 290})]
    hit = check_tailgating(tracks_frame(1.5, {1: 380, 2: 330}), history, LINE)
    assert hit is not None and hit.track_ids == [1, 2]


def test_tailgating_crossing_survives_missing_intermediate_detection():
    history = [
        tracks_frame(0.0, {1: 300}),
        tracks_frame(0.2, {}),
        tracks_frame(0.4, {1: 340}),
        tracks_frame(0.6, {1: 360, 2: 300}),
    ]
    hit = check_tailgating(tracks_frame(0.8, {1: 380, 2: 340}), history, LINE)
    assert hit is not None and hit.track_ids == [1, 2]


def test_single_person_no_tailgating():
    history = [tracks_frame(0, {1: 300})]
    assert check_tailgating(tracks_frame(0.5, {1: 340}), history, LINE) is None


def test_far_apart_no_tailgating():
    history = [tracks_frame(0, {1: 300}), tracks_frame(0.5, {1: 340}), tracks_frame(5, {2: 290})]
    assert check_tailgating(tracks_frame(6, {2: 330}), history, LINE) is None


def test_opposite_directions_no_tailgating():
    history = [tracks_frame(0, {1: 300, 2: 340})]
    assert check_tailgating(tracks_frame(1, {1: 340, 2: 300}), history, LINE) is None


def test_entry_direction_filter():
    history = [tracks_frame(0, {1: 300}), tracks_frame(0.5, {1: 340, 2: 290})]
    now = tracks_frame(1.5, {1: 380, 2: 330})
    both = EntranceLine(0.5, 0.0, 0.5, 1.0, entry_direction=None)
    wrong = EntranceLine(0.5, 0.0, 0.5, 1.0, entry_direction=1)  # these walk in direction -1
    assert check_tailgating(now, history, both) is not None
    assert check_tailgating(now, history, wrong) is None


def test_staying_on_opposite_side_does_not_repeat_crossing():
    frames = [
        tracks_frame(0.0, {1: 300}),
        tracks_frame(0.2, {1: 340}),
        tracks_frame(0.4, {1: 360}),
        tracks_frame(0.6, {1: 380}),
    ]
    assert _crossings(frames, LINE) == [(0.2, 1, -1)]


def test_track_missing_beyond_max_gap_does_not_cross():
    frames = [tracks_frame(0.0, {1: 300}), tracks_frame(2.0, {1: 340})]
    assert _crossings(frames, LINE, max_observation_gap_s=1.0) == []
