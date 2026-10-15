from pathlib import Path

from app.frame_pipeline import process_video
from app.schemas import Detection, FrameData
from tests.test_video_reader import make_video


class FakeTracker:
    """Pretends to detect 2 people and 1 backpack on every frame."""

    def update(self, frame):
        return [
            Detection(track_id=1, label="person", confidence=0.9, bbox=(1, 2, 30, 60)),
            Detection(track_id=2, label="person", confidence=0.8, bbox=(40, 2, 70, 60)),
            Detection(track_id=None, label="backpack", confidence=0.5, bbox=(5, 5, 10, 10)),
        ]


class BrokenTracker:
    def update(self, frame):
        raise RuntimeError("model crashed")


def test_process_video_makes_frame_data(tmp_path):
    video = tmp_path / "v.mp4"
    make_video(video)
    out = tmp_path / "frames"

    items = list(
        process_video(str(video), "cam1", FakeTracker(), target_fps=2.0, evidence_dir=str(out))
    )

    assert len(items) == 6
    first = items[0]
    assert isinstance(first, FrameData)
    assert first.camera_id == "cam1"
    assert (first.width, first.height) == (160, 120)
    assert first.person_count == 2
    assert first.wall_time is None
    assert Path(first.frame_path).is_file()
    assert [i.video_time_s for i in items] == sorted(i.video_time_s for i in items)


def test_failed_detection_is_skipped_not_crashed(tmp_path):
    video = tmp_path / "v.mp4"
    make_video(video)

    items = list(
        process_video(str(video), "cam1", BrokenTracker(), evidence_dir=str(tmp_path / "f"))
    )

    assert items == []