from app.id_stitcher import IdStitcher
from app.schemas import Detection


def person(track_id, x1, y1, x2, y2):
    return Detection(track_id=track_id, label="person", confidence=0.9, bbox=(x1, y1, x2, y2))


def test_fall_keeps_one_id():
    s = IdStitcher()
    assert s.apply([person(1, 100, 100, 160, 260)], 7.0)[0].track_id == 1      # standing
    assert s.apply([person(7, 60, 200, 300, 290)], 8.4)[0].track_id == 1       # fell, new raw id
    assert s.apply([person(9, 62, 202, 302, 292)], 10.2)[0].track_id == 1      # still lying, new raw id


def test_two_standing_people_stay_separate():
    s = IdStitcher()
    s.apply([person(1, 100, 100, 160, 260)], 1.0)
    out = s.apply([person(2, 105, 100, 165, 260)], 2.0)
    assert out[0].track_id == 2


def test_far_away_lying_person_is_not_merged():
    s = IdStitcher()
    s.apply([person(1, 100, 100, 160, 260)], 1.0)
    out = s.apply([person(5, 700, 400, 940, 490)], 2.5)
    assert out[0].track_id == 5

def test_gradual_fall_is_stitched():
    s = IdStitcher()
    s.apply([person(1, 100, 100, 179, 200)], 7.3)       # w/h = 0.79, still tilting
    out = s.apply([person(9, 90, 140, 190, 240)], 8.1)  # w/h = 1.00, new raw id
    assert out[0].track_id == 1