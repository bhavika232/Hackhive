"""Draw boxes + track IDs on a video so you can check the tracker by eye.

Usage:  python annotate_video.py path\\to\\video.mp4 [sample_fps] [output.mp4]
"""
import os
import sys

import cv2

from app.tracker import ObjectTracker
from app.video_reader import iter_frames

video = sys.argv[1]
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
out_path = sys.argv[3] if len(sys.argv) > 3 else "evidence/annotated.mp4"
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

tracker = ObjectTracker()
writer = None
font = cv2.FONT_HERSHEY_SIMPLEX

for sampled in iter_frames(video, "cam1", target_fps=fps, max_width=960):
    dets = tracker.update(sampled.frame)
    img = sampled.frame.copy()

    for d in dets:
        x1, y1, x2, y2 = map(int, d.bbox)
        color = (0, 255, 0) if d.label == "person" else (255, 128, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        tag = f"{d.label} #{d.track_id}" if d.track_id is not None else d.label
        cv2.putText(img, tag, (x1, max(15, y1 - 5)), font, 0.5, color, 1)

    people = sum(d.label == "person" for d in dets)
    cv2.putText(img, f"t={sampled.video_time_s:.1f}s people={people}", (10, 25), font, 0.7, (0, 0, 255), 2)

    if writer is None:
        h, w = img.shape[:2]
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    writer.write(img)

if writer:
    writer.release()
    print("Saved", out_path)
else:
    print("No frames processed.")