from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

import cv2
import numpy as np


@dataclass
class SampledFrame:
    """One sampled frame in memory. Used only inside Shreya's modules."""

    camera_id: str
    frame_index: int          # index in the ORIGINAL video
    video_time_s: float       # seconds from video start
    wall_time: Optional[str]  # ISO 8601 string, or None if unknown
    frame: np.ndarray         # BGR image (already resized if max_width was set)


def iter_frames(
    path: str,
    camera_id: str,
    target_fps: float = 2.0,
    start_wall_time: Optional[datetime] = None,
    max_width: Optional[int] = None,
) -> Iterator[SampledFrame]:
    """Yield sampled video frames with timestamps."""

    if target_fps <= 0:
        raise ValueError("target_fps must be greater than zero")

    video_path = Path(path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Cannot find video: {path}")

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        cap.release()
        raise ValueError(f"Cannot open video: {path}")

    try:
        src_fps = cap.get(cv2.CAP_PROP_FPS)

        if not src_fps or src_fps <= 0:
            raise ValueError("Could not determine source video FPS")

        frame_index = 0
        next_sample_time_s = 0.0
        sample_interval_s = 1.0 / target_fps

        while True:
            ok, frame = cap.read()

            if not ok:
                break

            video_time_s = frame_index / src_fps
            if video_time_s + 1e-9 >= next_sample_time_s:
                if max_width and frame.shape[1] > max_width:
                    scale = max_width / frame.shape[1]
                    frame = cv2.resize(frame, None, fx=scale, fy=scale)

                while next_sample_time_s <= video_time_s + 1e-9:
                    next_sample_time_s += sample_interval_s

                wall_time = (
                    (start_wall_time + timedelta(seconds=video_time_s)).isoformat()
                    if start_wall_time is not None
                    else None
                )

                yield SampledFrame(
                    camera_id=camera_id,
                    frame_index=frame_index,
                    video_time_s=video_time_s,
                    wall_time=wall_time,
                    frame=frame,
                )

            frame_index += 1

    finally:
        cap.release()
