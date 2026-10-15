from datetime import datetime

import cv2
import numpy as np

from app.video_reader import iter_frames


def make_video(path, n=30, fps=10):
    """Create a small synthetic video for testing."""
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (160, 120),
    )

    if not writer.isOpened():
        raise RuntimeError("Could not create test video")

    try:
        for i in range(n):
            frame = np.full((120, 160, 3), i * 8 % 255, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_sampling_and_timestamps(tmp_path):
    path = tmp_path / "test.mp4"
    make_video(path)

    frames = list(iter_frames(str(path), "cam1", target_fps=2.0))

    assert len(frames) == 6
    assert frames[0].camera_id == "cam1"

    times = [f.video_time_s for f in frames]
    assert times == sorted(times)
    assert abs(times[1] - 0.5) < 0.05
    assert frames[0].wall_time is None


def test_wall_time(tmp_path):
    path = tmp_path / "test.mp4"
    make_video(path)

    start = datetime(2026, 10, 15, 12, 0, 0)
    frames = list(iter_frames(str(path), "cam1", target_fps=2.0, start_wall_time=start))

    assert frames[2].wall_time == "2026-10-15T12:00:01"


def test_bad_path():
    try:
        list(iter_frames("does_not_exist.mp4", "cam1"))
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass