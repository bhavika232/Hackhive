"""Print person track IDs and box shape over time, to debug tracking.

Usage:  python id_timeline.py sample_videos\\fall_test.mp4 [sample_fps]
"""
import sys

from app.tracker import ObjectTracker
from app.video_reader import iter_frames

video = sys.argv[1]
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

tracker = ObjectTracker()
seen = set()

for sampled in iter_frames(video, "cam1", target_fps=fps, max_width=960):
    parts = []
    for d in tracker.update(sampled.frame):
        if d.label != "person":
            continue
        x1, y1, x2, y2 = d.bbox
        ratio = (x2 - x1) / max(1e-6, (y2 - y1))   # >1 means wider than tall
        parts.append(f"#{d.track_id}(w/h={ratio:.2f})")
        if d.track_id is not None:
            seen.add(d.track_id)
    print(f"t={sampled.video_time_s:5.1f}s  " + "  ".join(parts))

print(f"\nUnique person IDs over the clip: {len(seen)} -> {sorted(seen)}")