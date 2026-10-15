import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

import cv2

from app.schemas import Detection, FrameData
from app.video_reader import SampledFrame, iter_frames

logger = logging.getLogger(__name__)


def build_frame_data(
    sampled: SampledFrame,
    detections: list[Detection],
    frame_path: str,
) -> FrameData:
    """Turn one sampled frame plus its detections into the team's FrameData."""
    height, width = sampled.frame.shape[:2]
    return FrameData(
        camera_id=sampled.camera_id,
        frame_index=sampled.frame_index,
        video_time_s=sampled.video_time_s,
        wall_time=sampled.wall_time,
        frame_path=frame_path,
        width=width,
        height=height,
        detections=detections,
        person_count=sum(d.label == "person" for d in detections),
    )


def process_video(
    path: str,
    camera_id: str,
    tracker,
    target_fps: float = 2.0,
    start_wall_time: Optional[datetime] = None,
    max_width: Optional[int] = 960,
    evidence_dir: str = "evidence/frames",
) -> Iterator[FrameData]:
    """Read a video, track objects, save frames, and yield one FrameData per sampled frame.

    `tracker` is anything with .update(frame) -> list[Detection] (e.g. ObjectTracker).
    Bounding boxes are in the coordinates of the SAVED frame (after max_width resize).
    If detection fails on a frame, that frame is skipped (logged) and processing continues.
    """
    out_dir = Path(evidence_dir) / camera_id
    out_dir.mkdir(parents=True, exist_ok=True)

    for sampled in iter_frames(
        path,
        camera_id,
        target_fps=target_fps,
        start_wall_time=start_wall_time,
        max_width=max_width,
    ):
        try:
            detections = tracker.update(sampled.frame)
        except Exception as exc:
            logger.warning("Detection failed on frame %d: %s", sampled.frame_index, exc)
            continue

        frame_file = out_dir / f"f{sampled.frame_index:06d}.jpg"
        if not cv2.imwrite(str(frame_file), sampled.frame):
            logger.warning("Could not save frame %d to %s", sampled.frame_index, frame_file)
            continue

        yield build_frame_data(sampled, detections, frame_file.as_posix())