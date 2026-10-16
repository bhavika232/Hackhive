from app.id_stitcher import IdStitcher
from app.schemas import Detection


def person(track_id, x1, y1, x2, y2):
    return Detection(
        track_id=track_id,
        label="person",
        confidence=0.9,
        bbox=(x1, y1, x2, y2),
    )


def test_fall_keeps_one_id():
    stitcher = IdStitcher()
    assert stitcher.apply([person(1, 100, 100, 160, 260)], 7.0)[0].track_id == 1
    assert stitcher.apply([person(7, 60, 200, 300, 290)], 8.4)[0].track_id == 1
    assert stitcher.apply([person(9, 62, 202, 302, 292)], 10.2)[0].track_id == 1


def test_two_standing_people_stay_separate():
    stitcher = IdStitcher()
    stitcher.apply([person(1, 100, 100, 160, 260)], 1.0)
    out = stitcher.apply([person(2, 105, 100, 165, 260)], 2.0)
    assert out[0].track_id == 2


def test_far_away_lying_person_is_not_merged():
    stitcher = IdStitcher()
    stitcher.apply([person(1, 100, 100, 160, 260)], 1.0)
    out = stitcher.apply([person(5, 700, 400, 940, 490)], 2.5)
    assert out[0].track_id == 5


def test_gradual_fall_is_stitched():
    stitcher = IdStitcher()
    stitcher.apply([person(1, 100, 100, 179, 200)], 7.3)
    out = stitcher.apply([person(9, 90, 140, 190, 240)], 8.1)
    assert out[0].track_id == 1


def test_expired_raw_id_alias_is_not_reused():
    stitcher = IdStitcher()
    stitcher.apply([person(1, 100, 100, 160, 260)], 0.0)
    assert stitcher.apply([person(7, 60, 200, 300, 290)], 1.0)[0].track_id == 1
    stitcher.apply([], 31.1)
    out = stitcher.apply([person(7, 60, 200, 300, 290)], 32.0)
    assert out[0].track_id == 7


def test_non_person_detections_are_unchanged():
    stitcher = IdStitcher()
    item = Detection(track_id=1, label="backpack", confidence=0.8, bbox=(0, 0, 20, 20))
    assert stitcher.apply([item], 0.0) == [item]
