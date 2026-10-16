"""Benchmark detection + tracking speed at different sampling rates.

Usage:  python benchmark_fps.py path\\to\\video.mp4
"""
import platform
import sys
import time

from app.tracker import ObjectTracker
from app.video_reader import iter_frames

video = sys.argv[1] if len(sys.argv) > 1 else "sample_videos/test_video.mp4"
RATES = [5, 10, 15]  # sampling rates to test (frames per second of video)
MAX_FRAMES = 30      # frames per run
WIDTH = 960          # frames are resized to this width

print(f"Machine: {platform.processor() or platform.machine()} | Python {platform.python_version()}")
print(f"Video: {video} | resize width: {WIDTH}px\n")

rows = []
for fps in RATES:
    tracker = ObjectTracker()   # fresh tracker for each run
    infer_times = []
    start = time.perf_counter()

    for sampled in iter_frames(video, "bench", target_fps=fps, max_width=WIDTH):
        t0 = time.perf_counter()
        tracker.update(sampled.frame)
        infer_times.append(time.perf_counter() - t0)
        if len(infer_times) == MAX_FRAMES:
            break

    total = time.perf_counter() - start
    warm = infer_times[1:] or infer_times   # drop the first frame (warmup)
    avg_ms = sum(warm) / len(warm) * 1000
    rows.append((fps, len(infer_times), avg_ms, 1000 / avg_ms, len(infer_times) / total))

print(f"{'sample fps':>10} {'frames':>7} {'ms/frame':>9} {'max fps':>8} {'end-to-end fps':>15}")
for fps, n, ms, mx, e2e in rows:
    print(f"{fps:>10} {n:>7} {ms:>9.0f} {mx:>8.1f} {e2e:>15.1f}")

print("\nms/frame = detection+tracking only (first frame excluded).")
print("max fps = 1000 / ms-per-frame. If it's below the sample fps, a live stream falls behind.")
print("end-to-end fps includes reading and resizing the video, and the warmup frame.")