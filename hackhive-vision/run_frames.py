"""Run the full video -> FrameData pipeline on a video and print a summary.

Usage:  python run_pipeline.py sample_videos/test_video.mp4 5
"""
import sys
import time

from app.frame_pipeline import process_video
from app.tracker import ObjectTracker

video = sys.argv[1] if len(sys.argv) > 1 else "sample_videos/test_video.mp4"
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
max_frames = 15

tracker = ObjectTracker()
start = time.time()
count = 0

for count, fd in enumerate(process_video(video, "cam1", tracker, target_fps=fps), start=1):
    ids = sorted(d.track_id for d in fd.detections if d.label == "person" and d.track_id is not None)
    print(f"t={fd.video_time_s:5.2f}s people={fd.person_count} ids={ids} -> {fd.frame_path}")
    if count == 1:
        print("\nFirst FrameData (shortened):")
        print(fd.model_dump_json(indent=2)[:700], "...\n")
    if count == max_frames:
        break

if count:
    print(f"\n{count} frames in {time.time() - start:.1f}s total (includes model load + first-frame warmup)")
else:
    print("No frames processed.")